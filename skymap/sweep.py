"""Per-healpix density of dither-usable targets, CMX path vs main path.

Reads only RA/DEC and the one target-bit column from each healpix file, so the
sweep touches a few GB rather than the ~300 GB the catalogs occupy on disk.
"""
import os
import sys
from multiprocessing import Pool

import numpy as np
import fitsio
import healpy as hp

NSIDE = 32
NPIX = hp.nside2npix(NSIDE)
C = "/global/cfs/cdirs/desi/target/catalogs"

CATS = {
    "cmx":      (os.path.join(C, "dr9/0.49.0/targets/cmx/resolve/no-obscon"), "CMX_TARGET", "STD_DITHER"),
    "cmx_supp": (os.path.join(C, "gaiadr2/0.49.0/targets/cmx/resolve/supp"),  "CMX_TARGET", "STD_DITHER_GAIA"),
    "main":     (os.path.join(C, "gaiadr2/1.0.0/targets/main/resolve/backup"), "MWS_TARGET", "GAIA_STD_FAINT"),
    "main_bk":  (os.path.join(C, "gaiadr2/1.0.0/targets/main/resolve/backup"), "MWS_TARGET",
                 "GAIA_STD_FAINT|BACKUP_FAINT|BACKUP_VERY_FAINT"),
}


def bitval(col, expr):
    if col == "CMX_TARGET":
        from desitarget.cmx.cmx_targetmask import cmx_mask as m
    else:
        from desitarget.targetmask import mws_mask as m
    v = 0
    for name in expr.split("|"):
        v |= m[name].mask
    return v


def one_file(job):
    path, col, bv = job
    try:
        d = fitsio.read(path, columns=["RA", "DEC", col])
    except Exception:
        return np.zeros(NPIX, dtype=np.int64)
    keep = (d[col] & bv) > 0
    if keep.sum() == 0:
        return np.zeros(NPIX, dtype=np.int64)
    ipix = hp.ang2pix(NSIDE, d["RA"][keep], d["DEC"][keep], lonlat=True)
    return np.bincount(ipix, minlength=NPIX).astype(np.int64)


if __name__ == "__main__":
    out = {}
    for key, (d, col, expr) in CATS.items():
        bv = bitval(col, expr)
        fns = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".fits"))
        print("%-9s %4d files  %s  bitval=%d" % (key, len(fns), expr, bv), flush=True)
        with Pool(64) as p:
            maps = p.map(one_file, [(f, col, bv) for f in fns], chunksize=1)
        out[key] = np.sum(maps, axis=0)
        n = out[key]
        print("     total=%d  occupied pixels=%d/%d" % (n.sum(), (n > 0).sum(), NPIX), flush=True)
    np.savez("skymap/density_nside%d.npz" % NSIDE, nside=NSIDE, **out)
    print("saved skymap/density_nside%d.npz" % NSIDE)
