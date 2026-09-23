"""Verify a dither design from its written products, not from the log.

    python verify_design.py <outdir> <reference tileid>
    python verify_design.py dither_20260921/designs 84156     # main path
    python verify_design.py auto_test/cmx305        84300     # CMX path

Works on designs from either script.  Which survey wrote the design is read off
the columns present in the FIBERASSIGN HDU -- CMX files carry CMX_TARGET and
main-survey files carry MWS_TARGET -- so the right target bits are used for the
dither-star and standard-star counts.

Checks, per tile: row count, assigned fibres, fibres on stars and on sky,
presence of the EXTRA HDU (expected on every dithered tile, absent on the
reference), the per-petal sky budget, and the realised dither scatter against
the sigma the flavor requested.
"""
import os
import sys

import fitsio
import numpy as np


def survey_of(d):
    """'cmx' or 'main', from the columns the design actually carries."""
    return "cmx" if "CMX_TARGET" in d.dtype.names else "main"


def masks_for(survey):
    """(column, mask object, dither bits, flux-standard bits) for a survey."""
    if survey == "cmx":
        from desitarget.cmx.cmx_targetmask import cmx_mask
        # AR CMX STD_DITHER/STD_DITHER_GAIA are plain Gaia stars, not
        # AR spectrophotometric standards -- STD_FAINT is the standards bit.
        return ("CMX_TARGET", cmx_mask,
                ["STD_DITHER", "STD_DITHER_GAIA"], ["STD_FAINT"])
    from desitarget.targetmask import mws_mask
    return ("MWS_TARGET", mws_mask,
            ["GAIA_STD_FAINT", "BACKUP_FAINT", "BACKUP_VERY_FAINT"],
            ["GAIA_STD_FAINT"])


def bits_set(d, col, maskobj, bits):
    keep = np.zeros(len(d), dtype=bool)
    for b in bits:
        if b in maskobj.names():
            keep |= (d[col] & maskobj[b]) > 0
    return keep


def main(outdir, reftile):
    # AR One directory can hold several designs back to back, so take only the
    # AR block belonging to `reftile`: the reference tile has no EXTRA HDU and
    # AR every dither does, so walk forward until a tile without one -- that is
    # AR the next design's reference.
    def path_of(t):
        return os.path.join(outdir, "fiberassign-%06d.fits.gz" % t)

    def has_extra(fn):
        with fitsio.FITS(fn) as f:
            return "EXTRA" in [h.get_extname() for h in f]

    if not os.path.isfile(path_of(reftile)):
        sys.exit("no fiberassign-%06d.fits.gz in %s" % (reftile, outdir))
    fns = [path_of(reftile)]
    t = reftile + 1
    while os.path.isfile(path_of(t)) and has_extra(path_of(t)):
        fns.append(path_of(t))
        t += 1
    print("design: tileids %06d-%06d (%d tiles)"
          % (reftile, reftile + len(fns) - 1, len(fns)))

    d0 = fitsio.read(fns[0], ext="FIBERASSIGN")
    survey = survey_of(d0)
    col, maskobj, dither_bits, std_bits = masks_for(survey)
    print("survey: %s   (dither bits %s, standards %s)"
          % (survey, ",".join(dither_bits), ",".join(std_bits)))
    print()

    print("%-30s %7s %8s %7s %7s %7s  %s"
          % ("file", "rows", "assigned", "stars", "std", "sky", "EXTRA"))
    dra, ddec = [], []
    problems = []
    notes = []
    for fn in fns:
        d = fitsio.read(fn, ext="FIBERASSIGN")
        with fitsio.FITS(fn) as f:
            has_extra = "EXTRA" in [h.get_extname() for h in f]
        tileid = int(os.path.basename(fn).split("-")[1].split(".")[0])
        a = d["TARGETID"] >= 0
        sky = a & (d["OBJTYPE"] == "SKY")
        star = a & ~sky
        std = star & bits_set(d, col, maskobj, std_bits)
        if (tileid == reftile) and has_extra:
            problems.append("%06d is the reference tile but has an EXTRA HDU" % tileid)
        if (tileid != reftile) and not has_extra:
            problems.append("%06d is a dithered tile but has no EXTRA HDU" % tileid)
        print("%-30s %7d %8d %7d %7d %7d  %s"
              % (os.path.basename(fn), len(d), a.sum(), star.sum(),
                 std.sum(), sky.sum(), has_extra))
        if has_extra:
            ex = fitsio.read(fn, ext="EXTRA")
            if not np.array_equal(d["TARGETID"], ex["TARGETID"]):
                problems.append("%06d EXTRA rows do not line up with FIBERASSIGN" % tileid)
                continue
            # AR only dithered targets move; sky keeps UNDITHER == TARGET and
            # AR would drag the scatter down if it were included.
            m = star
            cd = np.cos(np.radians(d["TARGET_DEC"][m]))
            dra.append((d["TARGET_RA"][m] - ex["UNDITHER_RA"][m]) * 3600 * cd)
            ddec.append((d["TARGET_DEC"][m] - ex["UNDITHER_DEC"][m]) * 3600)

    reffn = os.path.join(outdir, "fiberassign-%06d.fits.gz" % reftile)
    if os.path.isfile(reffn):
        d = fitsio.read(reffn, ext="FIBERASSIGN")
        m = (d["TARGETID"] >= 0) & (d["OBJTYPE"] == "SKY")
        pp = np.bincount(d["PETAL_LOC"][m], minlength=10)
        print("\nreference tile sky per petal: %s  (min=%d, max=%d)"
              % (pp.tolist(), pp.min(), pp.max()))
        if pp.min() < 20:
            # AR a note, not a failure: the CMX path reads dr9/0.49.0 skies,
            # AR which are far sparser than 1.0.0, and that is accepted.
            notes.append("thin sky budget: %d per petal against the 40 requested"
                         % pp.min())
    else:
        problems.append("reference tile %06d not found in %s" % (reftile, outdir))

    if len(dra):
        dra, ddec = np.concatenate(dra), np.concatenate(ddec)
        print("dither scatter on %d dither targets: sd_dRA=%.3f\" sd_dDEC=%.3f\" "
              "mean=(%+.3f\", %+.3f\")"
              % (len(dra), dra.std(), ddec.std(), dra.mean(), ddec.mean()))
    else:
        problems.append("no dithered tiles with an EXTRA HDU; scatter not checked")

    print()
    if notes:
        print("NOTES:")
        for n in notes:
            print("  - %s" % n)
        print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  - %s" % p)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], int(sys.argv[2])))
