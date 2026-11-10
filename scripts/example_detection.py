"""Reproducible example: run the live detector on one small area and save the outputs to results/example/.

Usage (about 2-6 minutes on a laptop CPU, internet connection required):
    python scripts/example_detection.py
    python scripts/example_detection.py --bbox -112.20 36.05 -112.08 36.15 --dates 2026-05-15/2026-08-31

Inputs are read from public cloud archives (no account or API key):
  * Sentinel-2 L2A, Microsoft Planetary Computer, collection `sentinel-2-l2a` (scene IDs are saved in metadata.json)
  * USGS 3DEP 10 m DEM, Microsoft Planetary Computer, collection `3dep-seamless`
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))
import detector  # noqa: E402

DEFAULT_BBOX = (-112.20, 36.05, -112.08, 36.15)  # west, south, east, north - near Grand Canyon Village


def overlay(result):
    image = Image.fromarray(np.moveaxis(result['rgb'], 0, -1)).convert('RGB')
    draw = ImageDraw.Draw(image)
    t = result['transform']
    for geometry in result['detections'].geometry:
        points = [((x - t.c) / t.a, (y - t.f) / t.e) for x, y in geometry.exterior.coords]
        draw.line(points, fill=(34, 211, 238), width=4)
    return image


def main():
    parser = argparse.ArgumentParser(description='Run the CanyonScope detector on one area.')
    parser.add_argument('--bbox', nargs=4, type=float, default=DEFAULT_BBOX, metavar=('WEST', 'SOUTH', 'EAST', 'NORTH'))
    parser.add_argument('--dates', default='2026-05-15/2026-08-31', help='Sentinel-2 search window')
    parser.add_argument('--out', type=Path, default=REPO_DIR / 'results/example')
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    result = detector.detect_area(*args.bbox, date_range=args.dates)
    detections = result['detections']

    Image.fromarray(np.moveaxis(result['rgb'], 0, -1)).save(args.out / 'example_input_sentinel2.png')
    overlay(result).save(args.out / 'example_output_overlay.png')
    if len(detections):
        detections.to_crs(4326).to_file(args.out / 'example_detections.geojson', driver='GeoJSON')
    metadata = {
        'bbox_wgs84': list(args.bbox), 'date_range': args.dates, 'scene_date': result['scene_date'],
        'sentinel2_scene_ids': result['scene_ids'], 'model': 'models/seg_rgb_v2/best.pt',
        'confidence_threshold': detector.CONFIDENCE, 'tile_size_px': detector.TILE_SIZE, 'tile_step_px': detector.STEP,
        'detections': int(len(detections)),
        'canyon_area_km2': round(float(detections['area_km2'].sum()), 1) if len(detections) else 0.0,
        'mean_confidence': round(float(detections['mean_confidence'].mean()), 3) if len(detections) else None,
        'area_km2': result['area_km2'], 'runtime_seconds': round(time.time() - started),
    }
    (args.out / 'metadata.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
