import os
from astropy.table import Table
from desitarget.io import read_targets_in_tiles
C="/global/cfs/cdirs/desi/target/catalogs"
t=Table({"TILEID":[1],"RA":[305.],"DEC":[-20.],"OBSCONDITIONS":[3],"IN_DESI":[1],"PROGRAM":["DARK"]})
for name,path in [("dr9 skies",os.path.join(C,"dr9/1.0.0/skies")),
                  ("dr9 gfas",os.path.join(C,"dr9/1.0.0/gfas")),
                  ("gaiadr2 skies-supp",os.path.join(C,"gaiadr2/1.0.0/skies-supp")),
                  ("dr11 skies",os.path.join(C,"dr11/5.2.0/skies"))]:
    try:
        d=read_targets_in_tiles(path,tiles=t,quick=True)
        print("%-20s n=%d"%(name,len(d)))
    except Exception as e:
        print("%-20s ERR %s"%(name,repr(e)[:90]))
