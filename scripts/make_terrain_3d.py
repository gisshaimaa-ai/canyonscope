"""Make results/mars_analog/terrain_3d.npz for the 3D page: depth-below-plateau maps of both planets,
averaged over 4 x 4 cells (Earth 800 m, Mars about 6 km) so the 3D view stays fast."""
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1] / 'results/mars_analog'
SOURCES = {'earth': ('grand_canyon_incision_depth.tif', 1229.0),
           'mars': ('valles_marineris_incision_depth_light.tif', 9237.0)}
STEP = 4

output = {}
for name, (file_name, D) in SOURCES.items():
    with rasterio.open(ROOT / file_name) as src:
        depth = src.read(1).astype('float32')
        pixel = src.res[0]
    rows, cols = (depth.shape[0] // STEP) * STEP, (depth.shape[1] // STEP) * STEP
    small = depth[:rows, :cols].reshape(rows // STEP, STEP, cols // STEP, STEP).mean(axis=(1, 3))
    output[f'{name}_depth'] = small.astype('float16')
    output[f'{name}_pixel_m'] = np.float32(pixel * STEP)
    output[f'{name}_D_m'] = np.float32(D)
    print(name, small.shape, f'{pixel * STEP:.0f} m cells')

np.savez_compressed(ROOT / 'terrain_3d.npz', **output)
print('Saved', ROOT / 'terrain_3d.npz')
