# RTX 3090 graphics

The renderer uses the CUDA Recipes palette, Anton display type and IBM Plex Mono labels. Font files and OFL notices are in `fonts/`.

```sh
python3 -m venv .venv-render
.venv-render/bin/python -m pip install -r requirements-render.txt
.venv-render/bin/python scripts/make_charts.py
```

The two designs are `overview` and `decode-depth`, each provided as PNG and outlined SVG. `figure-data.json` identifies every plotted row and its exact values. Display labels are rounded; the measurement table preserves recorded precision.

The overview uses base UD-Q4_K_M tg128 and its verified 128K/256K decode. The depth graphic shows both Q4 artifacts. Error bars show sample standard deviation for the three-repetition points; single-repetition points have no estimated variation. Cache, batch and separate-host changes are stated explicitly. Depth points are not joined into a curve that assumes a common configuration.
