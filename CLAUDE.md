# dither_DESI

Fiber-assignment dithering scripts for DESI survey tiles.

## Environment: pin `desimodules/26.3`

**Do not use `desimodules/main`.** As of 2026-09 it ships numpy 2.5.3, under
which `desitarget.io.write_mtl` fails on *every* MTL write: it does
`int(np.unique(release // 1000))`, and converting a size-1 `ndim > 0` array to
a Python scalar raises `TypeError` from numpy 2.4 on. `write_mtl` catches it
and re-raises the misleading `"Multiple data releases in MTL ([9])"` — `[9]`
is a single release. Minimal reproducer:
`dither_20260921/repro_write_mtl_numpy2.py`.

```bash
source /global/common/software/desi/desi_environment.sh 26.3   # numpy 2.3.5, works
```

`fba_main_dither` probes for this at startup and exits 1 with an actionable
message rather than failing ~800 log lines into the run.

## Scripts

### `fba_main_dither`

Generates dithered fiber-assignment tiles for the **main DESI survey**.
Derived from `fba_cmx_new` (commissioning-era script); all dithering logic
is identical — only the target catalog inputs and bitmask columns differ.

**What it does:**

For a given tile centre and flavor it:
1. Writes per-tile `{tileid}-tiles.fits` files (one for the reference tile +
   one per dither offset)
2. Reads sky, GFA, and target catalogs via `read_targets_in_tiles`
3. Applies proper-motion corrections (`update_nowradec`)
4. For dithering flavors: tweaks `PRIORITY_INIT` by Gaia Rp magnitude so
   brighter standards get higher priority, then runs `fiberassign` once on
   the reference tile and once per dither with Gaussian (and optionally
   box) offsets applied to the assigned targets
5. Merges raw fba output, writes `fiberassign-{tileid}.fits.gz` files with
   an extra `EXTRA` HDU storing undithered positions, and produces
   diagnostic PNGs

**Flavors:**

| `--faflavor` | Program | Target mask | Dithers | σ |
|---|---|---|---|---|
| `dithprec` | DARK | per `--stdsource` (default `GAIA_STD_FAINT`) | 12 | 0.7″ Gaussian |
| `dithlost` | DARK | per `--stdsource` (default `GAIA_STD_FAINT`) | 2 | 50% Gaussian 2″ + 50% box 10″ |
| `dithfocus` | DARK | per `--stdsource` (default `GAIA_STD_FAINT`) | 12 | 2.0″ Gaussian |
| `scidark` | DARK | `LRG,ELG_LOP,QSO` | 0 | — |
| `scibright` | BRIGHT | `BGS_BRIGHT,BGS_FAINT` | 0 | — |

## Where the inputs come from

Two unrelated "DR" numbers are in play, and confusing them wastes time:

| input | tree | driven by |
|---|---|---|
| dither stars | `gaiadr2/{dtver}/targets/main/resolve/backup` | **hardcoded `"gaiadr2"`** |
| supp-skies | `gaiadr2/{dtver}/skies-supp` | **hardcoded `"gaiadr2"`** |
| science targets | `{dr}/{dtver}/targets/main/resolve/{dark,bright}` | `--dr` |
| skies | `{dr}/{dtver}/skies` | `--dr` |
| GFAs | `{dr}/{dtver}/gfas` | `--dr` |

`dr9`/`dr11` are **Legacy Surveys imaging** releases; `gaiadr2` is **Gaia's own**
release. `--dr dr11` moves skies and GFAs and leaves the dither stars untouched —
there is no `--dr` value that changes them. Only `--dtver` is shared, and it
indexes the desitarget processing version inside whichever tree, so bumping it
moves *both* trees at once.

**Do not bump `--dtver` to 2.2.0 for the Gaia catalog.** 2.2.0 is the newest
`gaiadr2` version that has targets at all (2.9.0+ ship only `skies-supp`), but
its backup selection is thinner: at 46 +2, `BACKUP_FAINT` drops 4590 → 3268
(−29%) and `BACKUP_VERY_FAINT` 3691 → 3080, while `GAIA_STD_FAINT` is unchanged
(1268 → 1269). Same 109 columns either way. Stay on 1.0.0.

## Dither standards: `--stdsource` (added 2026-09-21)

`STD_FAINT` is the main survey's **spectrophotometric calibration** standard
selection — deliberately sparse (~60/deg², 450–1500 per tile). Using it gave
designs with only ~300–950 stars on 5000 fibres, the rest sky.

**The CMX analogue is not `GAIA_STD_FAINT`.** CMX's `STD_DITHER`
(`isSTD_dither_spec`) was only `gaiagmag >= 11.5` and `gaiarmag >= 11.5` with no
colour cuts and no faint limit — plain Gaia stars. The off-footprint
`STD_DITHER_GAIA` added `aen < 1`, `astrometric_params_solved == 31` and an
effective G < 19. So the faithful analogue is `GAIA_STD_FAINT` **plus the
`BACKUP_*` bits**, which is what `--stdsource gaia+backup` does. `GAIA_STD_FAINT`
alone is the sparser standards selection — a large improvement over `STD_FAINT`,
but not a restoration of CMX behaviour.

| `--stdsource` | Masks | Tile obscon | Notes |
|---|---|---|---|
| `gaia` (default) | `GAIA_STD_FAINT` | `DARK\|GRAY` | 1268–17238 per tile |
| `gaia+backup` | `GAIA_STD_FAINT,BACKUP_FAINT,BACKUP_VERY_FAINT` | `DARK\|GRAY\|BACKUP` | ~4× more stars in sparse fields |
| `desi` | `STD_FAINT` | `DARK\|GRAY` | pre-2026-09 in-footprint behaviour |
| `auto` | either | `DARK\|GRAY` | `STD_FAINT` in-footprint, Gaia off-footprint (0.0.3) |

### `gaia+backup` does four things, and they must stay coupled

1. selects `GAIA_STD_FAINT,BACKUP_FAINT,BACKUP_VERY_FAINT`
2. widens the tile obscon to `DARK|GRAY|BACKUP`
3. applies `AEN < 1` and `params_solved == 31` to the **non-standard** targets
4. boosts `PRIORITY_INIT` by 200 for `GAIA_STD_FAINT`

They are one option rather than four flags because each is useless or harmful
alone:

- **Without (2) nothing happens at all.** `BACKUP_*` targets carry
  `OBSCONDITIONS = 568` = `BACKUP|TWILIGHT12|TWILIGHT18|IGNORE` — no DARK, no
  GRAY, no BRIGHT. `568 & 3 = 0`, so a `DARK|GRAY` tile drops every one of them.
  Measured: adding the masks alone moved 46 +2 from 829 to 857 stars.
- **Adding `BRIGHT` does not help.** `568 & 7 = 0` too. `BACKUP` (bit 8) is the
  only bit that admits them. CMX used `DARK|GRAY|BRIGHT`, which would also have
  failed here.
- **Without (4) you lose 40% of your flux standards** — they fall 833 → 497 as
  the `BACKUP` stars, six times more numerous, outrank them on the Rp-based
  priority. The +200 lifts standards clear of the whole Rp range (1000–1110).
- **(3)** matches the CMX `STD_DITHER_GAIA` astrometric cuts. Standards are
  exempt so a sparse field cannot lose them to a catalog quirk.

`make_mtl` recomputes `OBSCONDITIONS` from the target bits, so forcing it on the
target array before the MTL is written is silently discarded. Widening the tile
obscon is the correct mechanism; both routes give identical results (3225 stars).

### Measured at 46 +2 (the sparsest centre)

| | `gaia` | `gaia+backup` | + astrometric cut |
|---|---|---|---|
| candidates | 1268 | 8281 | 7692 |
| stars on fibres | 833 | 3227 | **3120** |
| true flux standards | 833 | 833 | **833** |
| sky / petal | 320–373 | 98–132 | 108–142 |
| median G | 17.3 | 17.5 | 17.5 |
| dither σ (req 0.7″) | 0.691/0.695″ | 0.690/0.701″ | 0.701/0.701″ |

The astrometric cut costs 3.3% of the stars. `BACKUP_BRIGHT` is deliberately
excluded — it reaches G = 10 and saturates in DARK; including it gives 3641.

### Astrometric quality (gaiadr2 2.2.0, 46 +2)

| selection | AEN < 1 | 5-param | no PM | drift > 0.7″ |
|---|---|---|---|---|
| `GAIA_STD_FAINT` | 1.000 | 1.000 | 0.000 | 0.000 |
| `BACKUP_BRIGHT` | 0.968 | 0.992 | 0.008 | 0.033 |
| `BACKUP_FAINT` | 0.968 | 0.983 | 0.017 | 0.024 |
| `BACKUP_VERY_FAINT` | 0.906 | 0.976 | 0.024 | 0.015 |

Gaia DR2's epoch is 2015.5, so a 2026 observation is an 11.2-year extrapolation;
"drift" is `|PM| × Δt`, the position error if proper motion were ignored. The
script *does* apply it (`update_nowradec`), so this is an upper bound. Note
`BACKUP_VERY_FAINT` drifts *less* than `BACKUP_BRIGHT` — nearby bright stars move
fastest, so faintness is not the risk here.

**`GAIA_STD_BRIGHT` is useless** — a strict *subset* of `GAIA_STD_FAINT` (both
start at G=16; BRIGHT stops at 18, FAINT continues to 19). At 0 +30 they hold
3111 and 2206 and their union is 3111. Never add the two counts; check overlap.

### Off-footprint / no-coverage fallback

Still present and unchanged: if the selected catalog returns 0 targets, the
script falls back to the Gaia backup catalog and sets `use_gaia_std = True` so
fiberassign receives the correct `gaia_stdmask`. With the default
`--stdsource gaia` this path is rarely reached.

## `fba_dither_auto` — picking the path automatically (added 2026-09-23)

Neither script works everywhere, so `fba_dither_auto` probes the tile centre and
execs whichever one suits it. Call it **without** `--dr`, `--dtver` or
`--stdsource`:

```bash
./fba_dither_auto --tilera 46 --tiledec -2 --tileid 84182 \
  --faflavor dithprec --rundate 2026-09-23T10:00:00+00:00 \
  --seed 80 --outdir ./designs/
```

`--dry-run` reports the decision without running (~20 s).
`--force {main,cmx}` skips the probe. `--min-targets` moves the bar.

### The rule — two paths, threshold on main only

```
main (--stdsource gaia, GAIA_STD_FAINT)   if it has >= --min-targets
cmx  (STD_DITHER / STD_DITHER_GAIA)       otherwise
```

The threshold is a question about the **main path only**: can the main-survey
catalog fill this focal plane? If yes, prefer it — its catalogs are current and
every assigned star is a flux standard. If no, fall to CMX, which is ~10×
denser everywhere but frozen at 2020 and yields almost no standards.

`--min-targets` defaults to **9000**, roughly where a design saturates the 4354
assignable fibres.

This is a **preference, not a maximum**: CMX is denser nearly everywhere
(61103 vs 9146 at 336 +30) and is still not chosen there. `--stdsource
gaia+backup` is deliberately *not* a rung — the dispatcher chooses between main
and CMX only.

### Measured decisions (threshold 9000)

| centre | main `GAIA_STD_FAINT` | CMX `STD_DITHER` | chosen |
|---|---|---|---|
| 336 +30 | 9146 | 61103 | main |
| 0 +30 | 3111 | 31850 | CMX |
| 46 +2 | 1268 | 13422 | CMX |
| 305 −20 | 17238 | 0 (supp: 70745) | main |
| 80 −40 | **0** | 30554 | CMX |

Verified end to end on both branches: 46 −2 gave 3032 stars / 857 standards via
the main path, 80 −40 gave 4121 stars via `fba_cmx_new`, 13 tiles each.

The dispatcher runs `os.makedirs` on `--outdir` before exec'ing, because both
underlying scripts call a bare `os.mkdir` that dies on a nested path.

## `fba_cmx_new` no longer gates on the DESI footprint (changed 2026-09-23)

It used to choose its target catalog purely from `is_point_in_desi()`:
in-footprint → `no-obscon`, out → `supp`, with **no fallback**. That is the wrong
question. A tile can sit inside the footprint and still have no `STD_DITHER`
coverage, and the script would then read an empty catalog and die.

It now probes both catalogs at the tile centre and uses whichever has more
targets. `tile_in_desi` is still computed (the plotting branch needs it) but no
longer decides anything.

Worked example — RA 305, Dec −20:

```
probe no-obscon:     0  STD_DITHER
probe supp:      70745  STD_DITHER_GAIA
using supp/STD_DITHER_GAIA  (tile_in_desi=1 was not used to decide)
-> 4348 stars assigned
```

Under the old logic that tile failed outright. `fba_main_dither` already had an
equivalent fallback; the two scripts now behave the same way.

## Sky coverage: where each path works

`skymap/dither_coverage.png`, built by `skymap/sweep.py` (per-healpix density
over 1827 catalog files, cached to `skymap/density_nside32.npz`) and
`skymap/plot_coverage.py`.

**`GAIA_STD_FAINT` stops dead at Dec = −30** — the DESI footprint's southern
limit. Not thinning: zero.

| Dec band | CMX usable | main usable |
|---|---|---|
| −90 to −60 | 100% | **0%** |
| −60 to −40 | 100% | **0%** |
| −40 to −30 | 97% | 11% |
| −35 to −25 | 97% | 52% |
| −30 to −20 | 98% | 95% |
| 0 to +20 | 100% | 99% |

At ≥1000 targets per tile: 73% of sky either works, **27% CMX-only** (almost all
the southern cap, plus the Galactic plane and the Magellanic Clouds), 0% main-only.
So below Dec −30 the CMX path is not a preference, it is the only option.

## CMX vs main at the same centre (RA 46, Dec +2)

The comparison Schlegel and Myers asked for. Same tile, same rundate:

| path | candidates | fibres | on stars | on sky | unassigned |
|---|---|---|---|---|---|
| CMX `STD_DITHER` | 13422 | 5000 | **3869** | 485 | 646 |
| main `--stdsource gaia` | 1268 | 5000 | **833** | 3521 | 646 |
| main `--stdsource gaia+backup` | 8281 | 5000 | 3120 | 1234 | 646 |

The **646 unassigned is identical** in all three — a positioner floor, not a
target-supply problem. No selection change touches it.

Their density figures check out: `GAIA_STD_FAINT` ≈ 158/deg², `STD_DITHER`
≈ 1680/deg².

**CMX buys stars by giving up standards**: it assigns only 127 true flux
standards against 833 for `gaia+backup`. That trade is the reason the ladder
prefers main while main can still fill the plane.

CMX catalogs live at `dr9/0.47.0` and `dr9/0.49.0` (`targets/cmx/resolve/no-obscon`)
with `gaiadr2/0.49.0/targets/cmx/resolve/supp` for off-footprint. `fba_cmx_new`
runs unmodified under `desimodules/26.3` — it still uses `np.in1d`, which exists
in numpy 2.3.5 and is gone in 2.5.3, so the same pin covers both scripts.

**Watch the sky budget on the CMX path.** At 80 −40 the design got only 6–18 sky
fibres per petal against the 40 requested, because `dr9/0.49.0` skies are much
sparser than `dr9/1.0.0`. The main path at 46 −2 got 100–153.

`verify_design.py` cannot check a CMX design: it counts
`MWS_TARGET & GAIA_STD_FAINT`, which CMX files do not have (they use
`CMX_TARGET`), so it reports 0 standards and a `nan` dither scatter.

## Key differences from `fba_cmx_new`

| Aspect | `fba_cmx_new` | `fba_main_dither` |
|---|---|---|
| Target mask | `cmx_mask` / `CMX_TARGET` | `desi_mask`, `bgs_mask`, `mws_mask` / `DESI_TARGET`, `BGS_TARGET`, `MWS_TARGET` |
| Dither std | `STD_DITHER` = plain Gaia, G>11.5, no colour cuts | `--stdsource gaia` = `GAIA_STD_FAINT` (standards only); `gaia+backup` = the faithful analogue |
| Dither std (off-footprint) | `STD_DITHER_GAIA` | `GAIA_STD_FAINT` |
| Science dark targets | `SV0_LRG,SV0_ELG,SV0_QSO` | `LRG,ELG_LOP,QSO` |
| Science bright targets | `SV0_BGS,SV0_MWS_FAINT` | `BGS_BRIGHT,BGS_FAINT` |
| Std stars for sci tiles | `SV0_WD,STD_FAINT/BRIGHT` | `STD_WD,STD_FAINT/BRIGHT` |
| Target dir (in-footprint) | `targets/cmx/resolve/no-obscon` | `targets/main/resolve/dark` or `bright` |
| Target dir (off-footprint) | `gaiadr2/.../targets/cmx/resolve/supp` | `gaiadr2/.../targets/main/resolve/supp` or `backup` |
| obscon | hardcoded `DARK\|GRAY\|BRIGHT` | per-flavor: `DARK\|GRAY` or `BRIGHT` |
| PROGRAM in tile file | `"CMX"` | `"DARK"` or `"BRIGHT"` |
| MTL / write survey | `survey="cmx"` | `survey="main"` |
| Monkey patch | patches `main_cmx_or_sv` for CMX bug | not needed |
| `starfaint` flavor | present | removed |
| `--dr` default | `dr8` | `dr9` |
| Off-footprint fallback | not present | auto-falls back when 0 targets found |

## Test commands (validated 2026-09-21)

Run inside an allocation, not on a login node. Each design (1 reference tile +
12 dithers) takes ~3-5 min and writes ~300 MB.

```bash
salloc --no-shell -A desi -C cpu -q interactive -t 04:00:00 -N 1
source /global/common/software/desi/desi_environment.sh 26.3
srun --jobid=<jobid> -n1 -c 32 ./dither_20260921/run_dither_20260921.sh
```

Driver scripts: `dither_20260921/run_dither_20260921.sh` (336 +30) and
`dither_20260921/run_305m20.sh` (305 -20). Diagnostics used to establish the
above live alongside them: `density.py`, `bright_check.py`, `backup_check.py`,
`dr11_check.py`, `cov305.py`, and `verify_design.py <outdir> <reference tileid>`,
which checks the written products (assignments, EXTRA HDU placement, per-petal
sky budget, realised dither scatter) rather than trusting the log.

