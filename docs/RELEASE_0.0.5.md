# 0.0.5 — `fba_dither_auto`

One self-contained script that picks its own catalogs. For dither designs it
replaces `fba_main_dither` and `fba_cmx_new`, which remain for science tiles.

```bash
source /global/common/software/desi/desi_environment.sh 26.3

./fba_dither_auto --tilera 46 --tiledec -2 --tileid 84182 \
  --faflavor dithprec --rundate 2026-09-23T10:00:00+00:00 \
  --seed 80 --outdir ./084/
```

No `--dtver`, no `--stdsource`. `--dry-run` reports the decision in ~5 s.

## Why

Neither old script worked everywhere. `GAIA_STD_FAINT` **stops dead at
Dec = −30** — zero, not thinning — which is what made designs fail "in some
cases". Across the sky 27% is CMX-only, 0% main-only.

## The rule

```
main   GAIA_STD_FAINT (gaiadr2/1.0.0)   if >= --min-targets
cmx    STD_DITHER / STD_DITHER_GAIA     otherwise
```

The threshold asks only whether **main** can fill the focal plane. If yes,
prefer it: current catalogs, every assigned star a flux standard. If no, CMX —
~10× denser, but frozen at 2020 and almost no standards (127 vs 833 at 46 +2).
Default 9000, where a design saturates the 4354 assignable fibres.

| centre | main | cmx | chosen |
|---|---|---|---|
| 336 +30 | 9146 | 61103 | main |
| 0 +30 | 3111 | 31850 | cmx |
| 46 +2 | 1268 | 13422 | cmx |
| 305 −20 | 17238 | 0 (supp 70745) | main |
| 80 −40 | **0** | 30554 | cmx |

At equal centre/seed/rundate it reproduces both originals exactly.

## Changes

- **New `fba_dither_auto`** — self-contained, dither flavors only.
  `--min-targets`, `--force main|cmx`, `--dry-run`.
- **No footprint gating.** Both scripts now probe for targets instead of using
  `is_point_in_desi()`. At 305 −20 the tile is *inside* the footprint but
  `no-obscon` holds 0 targets and `supp` holds 70745 — it used to fail outright.
- **`fba_main_dither --stdsource gaia+backup`** — adds `BACKUP_FAINT,
  BACKUP_VERY_FAINT`, widens obscon to `DARK|GRAY|BACKUP`, applies CMX
  astrometric cuts, boosts standards' priority. At 46 +2: 833 → 3120 stars,
  all 833 standards kept.
- **Startup guard** for the `desimodules/main` breakage — exits immediately
  instead of failing ~800 log lines in.
- **`verify_design.py` handles both surveys.** Also fixed: it checked every
  file in a directory holding several designs, and its dither scatter included
  sky fibres (0.62″ vs a requested 0.70″).
- **Docs** — sky coverage map, rewritten SurveyOps wiki page.

## Known limitations

- **Pin `26.3`.** `desimodules/main` ships numpy 2.5.3, under which
  `desitarget.io.write_mtl` fails on every write and blames the target catalog.
- **CMX sky budget** — 6–18 sky fibres per petal at 80 −40, 0 at 305 −20,
  against 40 requested. Accepted; reported as a NOTE.
- `GAIA_STD_BRIGHT` is a strict subset of `GAIA_STD_FAINT` — adding it gains
  nothing.

## Correction to 0.0.4

`GAIA_STD_FAINT` is *not* the analogue of CMX `STD_DITHER`. `STD_DITHER` was
`gaiagmag >= 11.5`, no colour cuts, no faint limit — so the analogue is
`GAIA_STD_FAINT` plus the `BACKUP_*` bits. This is why the threshold rule
prefers CMX in sparse fields.
