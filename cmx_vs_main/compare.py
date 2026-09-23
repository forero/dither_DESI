import os
import numpy as np
import fitsio

RUNS = [("CMX   (fba_cmx_new, STD_DITHER)",        "cmx",              84600),
        ("main  (gaia, GAIA_STD_FAINT)",           "main_gaia",        84620),
        ("main  (gaia+backup)",                    "main_gaiabackup",  84640)]

def cand(d, t):
    for ln in open(os.path.join("cmx_vs_main", d, "%06d.log" % t)):
        if "targets after having cut on" in ln and "keeping" in ln:
            return int(ln.split("keeping ")[1].split("/")[0])
    return -1

print("%-34s %10s %8s %8s %8s %10s"
      % ("path", "candidates", "fibers", "onstars", "onsky", "unassigned"))
for lbl, d, t in RUNS:
    fn = os.path.join("cmx_vs_main", d, "fiberassign-%06d.fits.gz" % t)
    fa = fitsio.read(fn, ext="FIBERASSIGN")
    a = fa["TARGETID"] >= 0
    sky = a & (fa["OBJTYPE"] == "SKY")
    star = a & ~sky
    print("%-34s %10d %8d %8d %8d %10d"
          % (lbl, cand(d, t), len(fa), star.sum(), sky.sum(), (~a).sum()))

print("\nper-design means over the 13 tiles:")
for lbl, d, t in RUNS:
    st, sk, un = [], [], []
    for tt in range(t, t + 13):
        fn = os.path.join("cmx_vs_main", d, "fiberassign-%06d.fits.gz" % tt)
        if not os.path.isfile(fn):
            continue
        fa = fitsio.read(fn, ext="FIBERASSIGN")
        a = fa["TARGETID"] >= 0
        sky = a & (fa["OBJTYPE"] == "SKY")
        st.append(int((a & ~sky).sum())); sk.append(int(sky.sum())); un.append(int((~a).sum()))
    print("  %-34s ntiles=%2d  onstars=%6.0f  onsky=%6.0f  unassigned=%6.0f"
          % (lbl, len(st), np.mean(st), np.mean(sk), np.mean(un)))
