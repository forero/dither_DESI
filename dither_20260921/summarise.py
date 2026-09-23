import os, numpy as np, fitsio
from desitarget.targetmask import mws_mask
D = os.path.join("dither_20260921", "designs")
BLOCKS = [("336 +30",84104),("  0 +30",84117),(" 15 +30",84130),
          (" 35 +30",84143),(" 46  +2",84156),("305 -20",84169)]
print("%-9s %-15s %6s %6s %6s %6s %5s %-13s %s"%(
    "centre","tileids","cand","stars","sky","assig","sky/petal","dither sd","EXTRA ok"))
for name, t0 in BLOCKS:
    cand = None
    with open(os.path.join(D, "%06d.log"%t0)) as f:
        for ln in f:
            if "targets after having cut on GAIA_STD_FAINT" in ln:
                cand = int(ln.split("keeping ")[1].split("/")[0]); break
    stars, sky, assig, dra, ddec, ok = [], [], [], [], [], True
    for t in range(t0, t0+13):
        fn = os.path.join(D, "fiberassign-%06d.fits.gz"%t)
        d = fitsio.read(fn, ext="FIBERASSIGN")
        with fitsio.FITS(fn) as f:
            names = [h.get_extname() for h in f]
        has_extra = "EXTRA" in names
        if (t == t0) == has_extra:          # AR reference must lack it, dithers must have it
            ok = False
        a = d["TARGETID"] >= 0
        s = a & ((d["MWS_TARGET"] & mws_mask["GAIA_STD_FAINT"]) > 0)
        stars.append(s.sum()); assig.append(a.sum())
        sky.append((a & (d["OBJTYPE"] == "SKY")).sum())
        if has_extra:
            ex = fitsio.read(fn, ext="EXTRA")
            cd = np.cos(np.radians(d["TARGET_DEC"][s]))
            dra.append((d["TARGET_RA"][s]-ex["UNDITHER_RA"][s])*3600*cd)
            ddec.append((d["TARGET_DEC"][s]-ex["UNDITHER_DEC"][s])*3600)
    d0 = fitsio.read(os.path.join(D, "fiberassign-%06d.fits.gz"%t0), ext="FIBERASSIGN")
    m = (d0["TARGETID"] >= 0) & (d0["OBJTYPE"] == "SKY")
    pp = np.bincount(d0["PETAL_LOC"][m], minlength=10)
    dra, ddec = np.concatenate(dra), np.concatenate(ddec)
    print("%-9s %06d-%06d %6d %6d %6d %6d %5s %.3f\"/%.3f\" %s"%(
        name, t0, t0+12, cand, int(np.mean(stars)), int(np.mean(sky)),
        int(np.mean(assig)), "%d-%d"%(pp.min(), pp.max()),
        dra.std(), ddec.std(), "yes" if ok else "NO"))
