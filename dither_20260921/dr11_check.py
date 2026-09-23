import numpy as np, tempfile, os
from astropy.table import Table
from desitarget.io import read_targets_in_tiles, write_mtl
from desitarget.targetmask import desi_mask, mws_mask
from desitarget.targets import decode_targetid
from desitarget.mtl import mtldatamodel
from desimodel.footprint import is_point_in_desi
import desimodel.io as dmio

C = "/global/cfs/cdirs/desi/target/catalogs"
D9  = os.path.join(C, "dr9/1.0.0/targets/main/resolve/dark")
D11 = os.path.join(C, "dr11/5.2.0/targets/main/resolve/dark")
BKP = os.path.join(C, "gaiadr2/1.0.0/targets/main/resolve/backup")
CEN = [(336., 30.), (0., 30.), (46., 2.), (305., -20.)]
tiles_all = dmio.load_tiles()

print("%-12s %7s %10s %11s %10s"%("centre","inDESI","dr9 STDF","dr11 STDF","gaia STDF"))
keep11 = None
for ra, dec in CEN:
    t = Table(); t["TILEID"]=[1]; t["RA"]=[ra]; t["DEC"]=[dec]
    t["OBSCONDITIONS"]=[3]; t["IN_DESI"]=[1]; t["PROGRAM"]=["DARK"]
    ind = int(is_point_in_desi(tiles_all, ra, dec))
    out = []
    for path in (D9, D11):
        try:
            d = read_targets_in_tiles(path, tiles=t, quick=True)
            n = int(((d["DESI_TARGET"] & desi_mask["STD_FAINT"]) > 0).sum())
            out.append(n)
            if path == D11 and keep11 is None and n > 0:
                keep11 = d[(d["DESI_TARGET"] & desi_mask["STD_FAINT"]) > 0]
        except Exception as e:
            out.append(-1)
    try:
        b = read_targets_in_tiles(BKP, tiles=t, quick=True)
        g = int(((b["MWS_TARGET"] & mws_mask["GAIA_STD_FAINT"]) > 0).sum())
    except Exception:
        g = -1
    print("%-12s %7d %10d %11d %10d"%("%g %+g"%(ra,dec), ind, out[0], out[1], g))

# --- the writing side ------------------------------------------------------
print("\n--- RELEASE / write_mtl for dr11 targets ---")
_, _, release, _, _, _ = decode_targetid(keep11["TARGETID"])
print("dr11 RELEASE unique:", np.unique(release), "-> DR int:", np.unique(release//1000))
d = np.zeros(len(keep11), dtype=mtldatamodel.dtype)
for k in ("RA","DEC","TARGETID","DESI_TARGET","BGS_TARGET","MWS_TARGET"):
    d[k] = keep11[k]
d["OBSCONDITIONS"] = 1; d["NUMOBS_MORE"] = 1
with tempfile.TemporaryDirectory() as tmp:
    try:
        n, fn = write_mtl(tmp, d, survey="main", ecsv=False)
        print("write_mtl(dr11) -> OK, %d rows, %s"%(n, os.path.basename(fn)))
    except Exception as e:
        print("write_mtl(dr11) -> %s: %s"%(type(e).__name__, e))

# mixing dr11 science + gaiadr2 standards in one MTL
print("\n--- mixing dr11 + gaiadr2 releases in one MTL ---")
b = read_targets_in_tiles(BKP, tiles=Table({"TILEID":[1],"RA":[336.],"DEC":[30.],
    "OBSCONDITIONS":[3],"IN_DESI":[1],"PROGRAM":["DARK"]}), quick=True)[:100]
d2 = np.zeros(len(keep11[:100]) + len(b), dtype=mtldatamodel.dtype)
d2["TARGETID"] = np.concatenate([keep11["TARGETID"][:100], b["TARGETID"]])
d2["OBSCONDITIONS"] = 1; d2["NUMOBS_MORE"] = 1
with tempfile.TemporaryDirectory() as tmp:
    try:
        write_mtl(tmp, d2, survey="main", ecsv=False); print("mixed -> OK")
    except Exception as e:
        print("mixed -> %s: %s"%(type(e).__name__, e))
