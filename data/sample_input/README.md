# Sample input

The app and `scripts/example_detection.py` read their imagery directly from public cloud archives, so no image
files are stored here (the requirements ask to keep heavy files out of GitHub).

Exact identifiers of the example run are in `example_inputs.json` (written by `scripts/example_detection.py`):

* **Imagery:** Microsoft Planetary Computer STAC API `https://planetarycomputer.microsoft.com/api/stac/v1`,
  collection `sentinel-2-l2a`, bands `B04`, `B03`, `B02`, cloud cover < 10 %.
* **Elevation:** same API, collection `3dep-seamless`, items with `gsd` = 10.
* **Area and dates:** see `example_inputs.json`.
