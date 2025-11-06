source /global/common/software/desi/desi_environment.sh main

./fba_cmx_new --dr dr9 --dtver 0.49.0 --rundate 2025-11-05T10:00:00+00:00 --seed 77 --tilera 5.0 --tiledec -31.5 --tileid 82983  --faflavor dithprec  --outdir ./
./fba_cmx_new --dr dr9 --dtver 0.49.0 --rundate 2025-11-05T10:00:00+00:00 --seed 77 --tilera 5.0 --tiledec -30.0 --tileid 82984  --faflavor dithprec  --outdir ./
./fba_cmx_new --dr dr9 --dtver 0.49.0 --rundate 2025-11-05T10:00:00+00:00 --seed 77 --tilera 5.0 --tiledec -28.5 --tileid 82985  --faflavor dithprec  --outdir ./

# This has very low number of SKY.
#./fba_cmx_new --dr dr9 --dtver 0.49.0 --rundate 2025-11-05T10:00:00+00:00 --seed 77 --tilera 150.0 --tiledec -31.5 --tileid 82986  --faflavor dithprec  --outdir ./
#./fba_cmx_new --dr dr9 --dtver 0.49.0 --rundate 2025-11-05T10:00:00+00:00 --seed 77 --tilera 150.0 --tiledec -30.0 --tileid 82987  --faflavor dithprec  --outdir ./
#./fba_cmx_new --dr dr9 --dtver 0.49.0 --rundate 2025-11-05T10:00:00+00:00 --seed 77 --tilera 150.0 --tiledec -28.5 --tileid 82988  --faflavor dithprec  --outdir ./

mkdir -p single_dither/
cp *-082983* single_dither 
cp *-082984* single_dither 
cp *-082985* single_dither 
#cp *-082986* single_dither 
#cp *-082987* single_dither 
#cp *-082988* single_dither 
