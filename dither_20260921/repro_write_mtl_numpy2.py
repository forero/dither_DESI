"""Minimal reproducer: desitarget.io.write_mtl fails under numpy >= 2.4.

Root cause: write_mtl does `drint = int(dr)` where `dr = np.unique(release//1000)`
is a *size-1 1-D array*.  Converting a size-1 (ndim>0) array to a Python scalar
was deprecated in numpy 1.25 and raises TypeError from numpy 2.4 on.  write_mtl
catches that TypeError and re-raises it as the misleading message
"Multiple data releases in MTL ([9])" -- there is only one data release.

  works:  source /global/common/software/desi/desi_environment.sh 26.3   (numpy 2.3.5)
  fails:  source /global/common/software/desi/desi_environment.sh main   (numpy 2.5.3)

  python repro_write_mtl_numpy2.py
"""
import tempfile
import numpy as np
from desitarget.io import write_mtl
from desitarget.mtl import mtldatamodel
from desitarget.targets import encode_targetid

print("numpy", np.__version__)

# --- the root cause, with no desitarget involved --------------------------
dr = np.unique(np.array([9000, 9000]) // 1000)   # -> array([9]), size 1, ndim 1
try:
    int(dr)
    print("int(np.unique(...)) -> OK")
except TypeError as e:
    print("int(np.unique(...)) -> TypeError:", e)

# --- the same thing surfacing through write_mtl ---------------------------
d = np.zeros(1, dtype=mtldatamodel.dtype)
d["TARGETID"] = encode_targetid(objid=1, brickid=1, release=9000)
d["OBSCONDITIONS"] = 1
d["NUMOBS_MORE"] = 1

with tempfile.TemporaryDirectory() as tmp:
    try:
        write_mtl(tmp, d, survey="main", ecsv=False)
        print("write_mtl -> OK")
    except TypeError as e:
        print("write_mtl -> TypeError:", e)
