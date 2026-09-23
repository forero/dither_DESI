# 0.0.5 — `fba_dither_auto`

Adds a single self-contained dither script that picks its own catalogs, and
fixes the reason designs were failing below Dec −30.

For dither designs, **`fba_dither_auto` is now the script to run.**
`fba_main_dither` and `fba_cmx_new` remain for science tiles and for reference.

```bash
source /global/common/software/desi/desi_environment.sh 26.3

./fba_dither_auto --tilera 46 --tiledec -2 --tileid 84182 \
  --faflavor dithprec --rundate 2026-09-23T10:00:00+00:00 \
  --seed 80 --outdir ./084/
```

No `--dtver`, no `--stdsource`. `--dry-run` reports the decision in ~5 s.

## Why

Neither existing script worked everywhere, and there was no way to tell which
one a given tile centre needed.

`GAIA_STD_FAINT` — the main survey's dither star catalog — **stops dead at
Dec = −30**, the DESI footprint's southern limit. Zero, not thinning. That is
what made designs fail "in some cases". Across the sky, 27% is CMX-only and 0%
is main-only.

| Dec band | CMX usable | main usable |
|---|---|---|
| −90 to −40 | 100% | **0%** |
| −40 to −30 | 97% | 11% |
| −30 to −20 | 98% | 95% |
| 0 to +20 | 100% | 99% |

## The rule

```
main   GAIA_STD_FAINT, gaiadr2/1.0.0 backup        if >= --min-targets
cmx    STD_DITHER (dr9/0.49.0 cmx no-obscon), or
       STD_DITHER_GAIA (gaiadr2/0.49.0 cmx supp)   otherwise
```

The threshold asks about the **main path only**: can the main catalog fill this
focal plane? If yes, prefer it — current catalogs, and every assigned star is a
flux standard. If no, fall to CMX: ~10× denser, but frozen at 2020 and assigning
almost no standards (127 against 833 at RA=46 Dec=+2).

`--min-targets` defaults to 9000, roughly where a design saturates the 4354
assignable fibres. It is a preference, not a maximum — CMX is denser at 336 +30
(61103 against 9146) and is still not chosen.

| centre | main | cmx | chosen |
|---|---|---|---|
| 336 +30 | 9146 | 61103 | main |
| 0 +30 | 3111 | 31850 | cmx |
| 46 +2 | 1268 | 13422 | cmx |
| 305 −20 | 17238 | 0 (supp 70745) | main |
| 80 −40 | **0** | 30554 | cmx |

At the same centre, seed and rundate it reproduces both originals exactly:
CMX at 46 +2 gives 3869 science / 127 standards / 450 sky, main at 336 +30 gives
3439 / 3439 / 394.

## Changes

**New — `fba_dither_auto`.** Self-contained; shells out to nothing. Dither
flavors only (`dithprec`, `dithlost`, `dithfocus`). `--min-targets`, `--force
main|cmx` and `--dry-run` replace `--dtver` and `--stdsource`.

**Fixed — `fba_cmx_new` no longer gates on the DESI footprint.** It chose its
catalog from `is_point_in_desi()` with no fallback, which is the wrong question:
a tile can sit inside the footprint and still have no coverage in the catalog
that test picks. At RA=305 Dec=−20, `no-obscon` holds 0 `STD_DITHER` while
`supp` holds 70745 `STD_DITHER_GAIA` — that tile failed outright and now
assigns 4348 fibres. Both scripts now probe for targets instead.

**Added — `fba_main_dither --stdsource gaia+backup`.** Selects
`GAIA_STD_FAINT,BACKUP_FAINT,BACKUP_VERY_FAINT`, widens the tile obscon to
`DARK|GRAY|BACKUP`, applies the CMX astrometric cuts (`AEN < 1`, 5-parameter
solution) to the non-standard targets, and boosts standards' priority so none
are crowded out. At 46 +2: 833 → 3120 stars with all 833 flux standards kept.
The four effects are one option because each is useless alone — without the
obscon change the extra bits do nothing at all.

**Added — startup guard for the numpy/`write_mtl` breakage.** `desimodules/main`
ships numpy 2.5.3, under which `desitarget.io.write_mtl` fails on every MTL
write and reports it as the misleading `"Multiple data releases in MTL ([9])"`.
The scripts now exit immediately with the command to source the pinned release
rather than failing hundreds of log lines in. Reproducer included.

**Improved — `verify_design.py` handles both surveys.** It only understood
main-survey output, so CMX designs came back with 0 standards and a `nan` dither
scatter. Also fixed: it checked every file in the output directory, so verifying
one design in a directory holding several reported the others' reference tiles
as broken; and the dither scatter included sky fibres, which keep
`UNDITHER == TARGET` and pulled the measured sigma to 0.62″ against a requested
0.70″.

**Docs.** Sky coverage map (`skymap/dither_coverage.png`) plus the sweep that
builds it; rewritten SurveyOps wiki page; CLAUDE.md covering catalog provenance
(`dr9`/`dr11` are Legacy Surveys releases, `gaiadr2` is Gaia's own and is
hardcoded), and why `--dtver 2.2.0` is a step backwards.

## Known limitations

**CMX sky budget.** CMX designs read `dr9/0.49.0` skies, far sparser than
`1.0.0`: 6–18 sky fibres per petal at 80 −40 and 0 at 305 −20, against the 40
requested. Accepted; `verify_design.py` reports it as a NOTE and still passes.

**Pin the environment.** `source /global/common/software/desi/desi_environment.sh 26.3`.
`desimodules/main` cannot run these scripts.

**`GAIA_STD_BRIGHT` is a strict subset of `GAIA_STD_FAINT`** — adding it gains
nothing.

## Correction to 0.0.4 documentation

0.0.4 stated that `GAIA_STD_FAINT` is the main-survey analogue of the CMX
`STD_DITHER` mask. It is not. `STD_DITHER` was `gaiagmag >= 11.5` with no colour
cuts and no faint limit — plain Gaia stars — so the analogue is `GAIA_STD_FAINT`
plus the `BACKUP_*` bits. `GAIA_STD_FAINT` alone is the sparser
spectrophotometric standard selection: a large improvement over `STD_FAINT`, but
not a restoration of CMX behaviour.
