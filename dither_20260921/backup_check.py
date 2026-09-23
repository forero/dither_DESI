import numpy as np
from astropy.table import Table
from desitarget.io import read_targets_in_tiles
from desitarget.targetmask import mws_mask

CEN=[(336.,30.),(0.,30.),(15.,30.),(35.,30.),(46.,2.)]
bkp="/global/cfs/cdirs/desi/target/catalogs/gaiadr2/1.0.0/targets/main/resolve/backup"
BITS=["BACKUP_BRIGHT","BACKUP_FAINT","BACKUP_VERY_FAINT"]

print("%-12s %8s %8s %8s %8s %8s"%("centre","STDFAINT","BK_BR","BK_FA","BK_VF","union_all"))
rows=[]
for ra,dec in CEN:
    t=Table(); t["TILEID"]=[1]; t["RA"]=[ra]; t["DEC"]=[dec]
    t["OBSCONDITIONS"]=[3]; t["IN_DESI"]=[1]; t["PROGRAM"]=["DARK"]
    b=read_targets_in_tiles(bkp,tiles=t,quick=True)
    sf=(b["MWS_TARGET"]&mws_mask["GAIA_STD_FAINT"])>0
    sels={m:(b["MWS_TARGET"]&mws_mask[m])>0 for m in BITS}
    u=sf.copy()
    for m in BITS: u|=sels[m]
    print("%-12s %8d %8d %8d %8d %8d"%("%g %+g"%(ra,dec),sf.sum(),
          sels["BACKUP_BRIGHT"].sum(),sels["BACKUP_FAINT"].sum(),
          sels["BACKUP_VERY_FAINT"].sum(),u.sum()))
    rows.append((ra,dec,b,sf,sels))

print("\nG range per bit (min/med/max), and overlap with GAIA_STD_FAINT")
for ra,dec,b,sf,sels in rows:
    g=b["GAIA_PHOT_G_MEAN_MAG"]
    for m in BITS:
        s=sels[m]
        print("%-12s %-17s n=%6d G=%5.2f/%5.2f/%5.2f  in_STD_FAINT=%6d"%(
            "%g %+g"%(ra,dec),m,s.sum(),g[s].min(),np.median(g[s]),g[s].max(),(s&sf).sum()))
