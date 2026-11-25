# CUDA Recipes 009 graphics

These figures use the Major Minor research palette and frame: warm paper, Anton display type, IBM Plex Mono labels, fine rules, and the blue/rust/ink series colors used by earlier CUDA Recipes graphics. Each chart is supplied as PNG and outlined SVG.

`figure-data.json` contains the exact values used in the charts. Display labels retain the recorded precision. Filled-context rows are grouped by depth and are not connected, because KV type and batch/ubatch change at larger depths. The MTP server comparison uses three fixed prompts and is a separate measurement from `llama-bench` and the quality suite.

To regenerate:

```sh
python3 -m pip install -r requirements-render.txt
python3 scripts/make_charts.py
```
