import os, fitsio
C = "/global/cfs/cdirs/desi/target/catalogs"
for lbl, d in [("CMX no-obscon", os.path.join(C,"dr9/0.49.0/targets/cmx/resolve/no-obscon")),
               ("CMX supp",      os.path.join(C,"gaiadr2/0.49.0/targets/cmx/resolve/supp")),
               ("main backup",   os.path.join(C,"gaiadr2/1.0.0/targets/main/resolve/backup"))]:
    fns = sorted(f for f in os.listdir(d) if f.endswith(".fits"))
    p = os.path.join(d, fns[0])
    with fitsio.FITS(p) as f:
        h = f[1].read_header()
        keys = [k for k in ("FILENSID","FILENEST","HPXPIXEL","HPXNSIDE","NAXIS2") if k in h]
        print("%-14s nfiles=%4d  first=%s" % (lbl, len(fns), fns[0]))
        print("     header: %s" % {k: h[k] for k in keys})
        print("     size: %.1f MB  rows=%d" % (os.path.getsize(p)/1e6, h["NAXIS2"]))
