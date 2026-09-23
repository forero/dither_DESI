"""Candidate counts for the CMX and main paths at RA=46, Dec=+2 and Dec=-2."""
import os
import numpy as np
from astropy.table import Table
from desitarget.io import read_targets_in_tiles
from desitarget.cmx.cmx_targetmask import cmx_mask
from desitarget.targetmask import mws_mask

C = "/global/cfs/cdirs/desi/target/catalogs"
CMX  = os.path.join(C, "dr9/0.49.0/targets/cmx/resolve/no-obscon")
CSUP = os.path.join(C, "gaiadr2/0.49.0/targets/cmx/resolve/supp")
MAIN = os.path.join(C, "gaiadr2/1.0.0/targets/main/resolve/backup")

for ra, dec in [(46.0, 2.0), (46.0, -2.0)]:
    t = Table({"TILEID":[1],"RA":[ra],"DEC":[dec],"OBSCONDITIONS":[3],
               "IN_DESI":[1],"PROGRAM":["DARK"]})
    print("=== RA=%g Dec=%+g ===" % (ra, dec))
    for lbl, path, col, mask, bits in [
            ("CMX no-obscon", CMX,  "CMX_TARGET", cmx_mask,
             ["STD_DITHER", "STD_GAIA", "STD_FAINT"]),
            ("CMX supp(gaia)", CSUP, "CMX_TARGET", cmx_mask,
             ["STD_DITHER_GAIA"]),
            ("main backup",   MAIN, "MWS_TARGET", mws_mask,
             ["GAIA_STD_FAINT", "BACKUP_FAINT", "BACKUP_VERY_FAINT"])]:
        try:
            d = read_targets_in_tiles(path, tiles=t, quick=True)
        except Exception as e:
            print("  %-16s ERROR %s" % (lbl, repr(e)[:80]))
            continue
        parts = []
        for b in bits:
            if b in mask.names():
                parts.append("%s=%d" % (b, int(((d[col] & mask[b]) > 0).sum())))
        # AR PSF fraction where a morphology column exists
        psf = ""
        if "TYPE" in d.dtype.names and len(d):
            ty = d["TYPE"]
            ty = np.array([x.decode().strip() if isinstance(x, bytes) else str(x).strip() for x in ty])
            psf = "  PSF=%.2f" % (ty == "PSF").mean()
        print("  %-16s N=%6d   %s%s" % (lbl, len(d), "  ".join(parts), psf))
    print()
