#!/bin/bash
# AR Dither designs, 2026-09-21.
#
# AR Rebuilt with --stdsource gaia: the main-survey STD_FAINT selection gave
# AR only ~450-1500 candidates per tile (~300-950 assigned fibres, rest sky).
# AR GAIA_STD_FAINT from the Gaia backup catalog gives ~1300-17000.
#
# AR TILEIDs continue from the last tile committed to
# AR https://desi.lbl.gov/svn/data/tiles/trunk/084 , which is 084103.
# AR Each design occupies 13 consecutive ids (1 reference + 12 dithers).
# AR The first five match the ids already used for these centres.
#
# AR Run inside an allocation, not on a login node:
# AR   salloc --no-shell -A desi -C cpu -q interactive -t 04:00:00 -N 1
# AR   srun --jobid=<id> -n1 -c 32 ./dither_20260921/run_dither_20260921.sh

set -e
export HOSTNAME=${HOSTNAME:-perlmutter}

# AR desimodules/main ships numpy 2.5, under which desitarget.io.write_mtl
# AR dies with the misleading "Multiple data releases in MTL".  26.3 works.
# AR fba_main_dither also checks this at startup and exits 1 if it is wrong.
source /global/common/software/desi/desi_environment.sh 26.3

OUTDIR=./dither_20260921/designs/
RUNDATE=2026-09-21T10:00:00+00:00
DTVER=1.0.0
SEED=80

# AR  RA     DEC   TILEID   (block = TILEID .. TILEID+12)
CENTRES=(
  "336.0  30.0  84104"
  "  0.0  30.0  84117"
  " 15.0  30.0  84130"
  " 35.0  30.0  84143"
  " 46.0   2.0  84156"
  "305.0 -20.0  84169"
)

mkdir -p ${OUTDIR}

for c in "${CENTRES[@]}"; do
  set -- $c
  ra=$1; dec=$2; tid=$3
  echo "=== tile ${tid}: RA=${ra} DEC=${dec} ==="
  ./fba_main_dither \
    --dr dr9 --dtver ${DTVER} --rundate ${RUNDATE} --seed ${SEED} \
    --tilera ${ra} --tiledec ${dec} --tileid ${tid} \
    --faflavor dithprec --stdsource gaia --outdir ${OUTDIR}
done
echo "=== all designs complete ==="
