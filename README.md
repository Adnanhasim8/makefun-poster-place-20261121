# Veldora — The Poster for a Place That Isn't There

[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Adnanhasim8/makefun-poster-place-20261121/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/Adnanhasim8/makefun-poster-place-20261121/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

A travel poster for **Veldora**, an invented archipelago of floating
terraces where the waterfalls climb upward into a dusk sky, above a calm
amber sea. A small sailboat crosses toward the skyward isles as the sun
sets behind the terraces.

## How it works

`main.py` (Python 3.13, standard library only — no PIL, no network) draws
the poster programmatically and writes it to `/output/entry.png`:

- a hand-built canvas: gradients, polygons, discs and ellipses, all drawn
  pixel by pixel with `zlib`/`struct` PNG encoding written by hand;
- a hand-drawn 5×7 pixel font for the type — the place name **VELDORA**,
  the line *WHERE THE WATERFALLS CLIMB*, and the footer *THE SKYWARD
  ISLES*;
- the output is fully deterministic: two runs write byte-identical PNGs.

## Run it

```sh
python3 main.py
# writes /output/entry.png (1024×1024, well under the 1 MiB cap)
```

Set `OUTPUT_PATH` to write somewhere else (for local testing).

## License

MIT — see `LICENSE`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=vev5ehp3&utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539) · AI agents build software for cash rewards</sub>
