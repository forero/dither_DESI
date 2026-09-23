# dither_DESI

Fiber-assignment dithering scripts for DESI survey tiles.

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
| `dithprec` | DARK | `STD_FAINT` / `GAIA_STD_FAINT` | 12 | 0.7″ Gaussian |
| `dithlost` | DARK | `STD_FAINT` / `GAIA_STD_FAINT` | 2 | 50% Gaussian 2″ + 50% box 10″ |
| `dithfocus` | DARK | `STD_FAINT` / `GAIA_STD_FAINT` | 12 | 2.0″ Gaussian |
| `scidark` | DARK | `LRG,ELG_LOP,QSO` | 0 | — |
| `scibright` | BRIGHT | `BGS_BRIGHT,BGS_FAINT` | 0 | — |

## Off-footprint Gaia fallback

For dithering flavors (`dithprec`, `dithlost`, `dithfocus`) the script
selects dither standards in this order:

1. **`tile_in_desi == True`** → read from `dr9/{dtver}/targets/main/resolve/dark`,
   filter on `STD_FAINT` (DESI_TARGET bit 33)
2. **`tile_in_desi == False`** → read from `gaiadr2/{dtver}/targets/main/resolve/`
   (`supp` for dtver ≤ 0.x, `backup` for dtver ≥ 1.0), filter on
   `GAIA_STD_FAINT` (MWS_TARGET bit 33), pass `gaia_stdmask` to fiberassign
3. **Fallback (tile in footprint but catalog has no coverage)** → if step 1
   returns 0 targets, automatically fall back to step 2. Sets
   `tile_in_desi = 0` so fiberassign receives the correct `gaia_stdmask`.
   This happens when a catalog version covers only a partial footprint
   

## Key differences from `fba_cmx_new`

| Aspect | `fba_cmx_new` | `fba_main_dither` |
|---|---|---|
| Target mask | `cmx_mask` / `CMX_TARGET` | `desi_mask`, `bgs_mask`, `mws_mask` / `DESI_TARGET`, `BGS_TARGET`, `MWS_TARGET` |
| Dither std (in-footprint) | `STD_DITHER` | `STD_FAINT` |
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

## Test commands (validated 2026-04-29)

Off-footprint tile (RA=250 Dec=-5, outside DESI footprint) with dtver 0.49.0:
```bash
source /global/common/software/desi/desi_environment.sh main
./fba_main_dither --dr dr9 --dtver 0.49.0 --rundate 2026-04-29T10:00:00+00:00 \
  --seed 80 --tilera 250 --tiledec -5.0 --tileid 84104 \
  --faflavor dithprec --outdir ./
```

Off-footprint tile with dtver 1.0.0 (uses `backup` instead of `supp`):
```bash
./fba_main_dither --dr dr9 --dtver 1.0.0 --rundate 2026-04-29T10:00:00+00:00 \
  --seed 80 --tilera 250 --tiledec -5.0 --tileid 84104 \
  --faflavor dithprec --outdir ./dtver_1.0.0
```

In-footprint tile outside partial catalog coverage (triggers Gaia fallback):
```bash
./fba_main_dither --dr dr9 --dtver 1.0.0 --rundate 2026-04-29T10:00:00+00:00 \
  --seed 80 --tilera 190 --tiledec -25.0 --tileid 84104 \
  --faflavor dithprec --outdir ./dtver_1.0.0_cmx_fail
```

## Target-class trade-off: CMX vs main (open question, 2026-09-23)

Choosing between `fba_cmx_new` and `fba_main_dither` is not just a code
version choice; it changes how many fibers a dither tile can actually use.

The main-survey standards (`STD_FAINT` / `GAIA_STD_FAINT`) are selected as
*potential spectrophotometric standards*, so they keep only the bluest
stars. The commissioning classes (`STD_DITHER` / `STD_DITHER_GAIA`) are a
much looser cut and are far more plentiful.

Densities measured by Adam Myers and David Schlegel near RA, Dec = 46, -2:

| Quantity | Per sq. deg. |
|---|---|
| All Gaia sources | ~2900 |
| Gaia sources with `type == PSF` | ~2600 (90%) |
| `GAIA_STD_FAINT` | ~150 |

A DESI tile covers ~7.1 sq. deg., so the main-survey selection yields only
~1000 dither standards per tile while ~20x more Gaia point sources are
available. Dithers could in principle use any PSF source, so restricting to
`GAIA_STD_FAINT` leaves most fibers unused.

The counter-argument, and the reason the main-survey path was written in the
first place, is **footprint**: the CMX targeting files have no coverage at
some low declinations, where a dither design returns zero targets. The
main-survey files plus the Gaia backup fallback cover much more sky.

Commissioning target definitions:
https://desi.lbl.gov/trac/wiki/TargetSelectionWG/CommissioningTargets#STD_DITHER

The dr9/cmx targets are still on disk at NERSC, so `fba_cmx_new` should
still run, modulo version skew in the desi environment.

**To do:** compare fiber usage from both paths at the same tile centre
(start at RA, Dec = 46, -2), then make the CMX-vs-main switch a single
option rather than two separate scripts. Related: the dither scripts also
need to build from DR11 to reach Dec = -20.
