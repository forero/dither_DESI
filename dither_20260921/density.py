import numpy as np, os
from astropy.table import Table
from desitarget.io import read_targets_in_tiles
from desitarget.targetmask import desi_mask, mws_mask

CEN=[(336.,0.),(0.,30.),(15.,30.),(35.,30.),(46.,2.)]
CAT="/global/cfs/cdirs/desi/target/catalogs"
dark=os.path.join(CAT,"dr9/1.0.0/targets/main/resolve/dark")
bkp =os.path.join(CAT,"gaiadr2/1.0.0/targets/main/resolve/backup")

for ra,dec in CEN:
    t=Table(); t["TILEID"]=[1]; t["RA"]=[ra]; t["DEC"]=[dec]; t["OBSCONDITIONS"]=[3]
    t["IN_DESI"]=[1]; t["PROGRAM"]=["DARK"]
    out=[f"RA={ra} DEC={dec}"]
    try:
        d=read_targets_in_tiles(dark,tiles=t,quick=True)
        out.append("  dark: N=%d STD_FAINT=%d STD_BRIGHT=%d"%(len(d),
            ((d["DESI_TARGET"]&desi_mask["STD_FAINT"])>0).sum(),
            ((d["DESI_TARGET"]&desi_mask["STD_BRIGHT"])>0).sum()))
    except Exception as e: out.append("  dark: ERR %s"%e)
    try:
        b=read_targets_in_tiles(bkp,tiles=t,quick=True)
        s=["N=%d"%len(b)]
        for m in ["GAIA_STD_FAINT","GAIA_STD_BRIGHT","GAIA_STD_WD","BACKUP_BRIGHT","BACKUP_FAINT","BACKUP_VERY_FAINT"]:
            if m in mws_mask.names():
                s.append("%s=%d"%(m,((b["MWS_TARGET"]&mws_mask[m])>0).sum()))
        out.append("  backup: "+" ".join(s))
        g=b["GAIA_PHOT_G_MEAN_MAG"]
        for lo,hi in [(12,16),(16,18),(16,19),(12,19)]:
            out.append("    backup G in [%g,%g): %d"%(lo,hi,((g>=lo)&(g<hi)).sum()))
    except Exception as e: out.append("  backup: ERR %s"%e)
    print("\n".join(out),flush=True)
