"""Sky maps: where each dither script has targets.

Panels 1-2 are the same measure (usable dither targets per tile) for the two
paths, so they share one blue ramp and one scale -- small multiples, not two
sequential contexts. Panel 3 is categorical: which script to use where.
"""
import numpy as np
import healpy as hp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, BoundaryNorm, LogNorm
from matplotlib.patches import Patch

# --- palette (dataviz reference instance) ---------------------------------
SEQ = ["#cde2fb","#b7d3f6","#9ec5f4","#86b6ef","#6da7ec","#5598e7","#3987e5",
       "#2a78d6","#256abf","#1c5cab","#184f95","#104281","#0d366b"]
CAT = {"both": "#2a78d6", "cmx": "#eb6834", "main": "#1baf7a"}
NEUTRAL   = "#e6e5e1"
SURFACE   = "#fcfcfb"
INK       = "#0b0b0b"
INK2      = "#52514e"
GRID      = "#c9c8c2"

TILE_AREA = 8.0          # deg^2, DESI tile
USABLE    = 1000         # targets per tile to call a field usable

d = np.load("skymap/density_nside32.npz")
NSIDE = int(d["nside"])
PIXAREA = hp.nside2pixarea(NSIDE, degrees=True)

def per_tile(counts):
    return counts / PIXAREA * TILE_AREA

maps = {k: per_tile(d[k].astype(float)) for k in ("cmx", "cmx_supp", "main", "main_bk")}
# AR the CMX path uses no-obscon in the footprint and the gaia supp file outside it
maps["cmx_any"] = np.maximum(maps["cmx"], maps["cmx_supp"])

# --- resample healpix onto an RA/Dec grid ---------------------------------
NRA, NDEC = 1440, 720
ra_edges = np.linspace(360.0, 0.0, NRA + 1)
dec_edges = np.linspace(-90.0, 90.0, NDEC + 1)
ra_c = 0.5 * (ra_edges[:-1] + ra_edges[1:])
dec_c = 0.5 * (dec_edges[:-1] + dec_edges[1:])
RA, DEC = np.meshgrid(ra_c, dec_c)
IPIX = hp.ang2pix(NSIDE, RA, DEC, lonlat=True)

def grid(m):
    return m[IPIX]

# --- figure ---------------------------------------------------------------
fig, axes = plt.subplots(3, 1, figsize=(13.5, 14.0), facecolor=SURFACE)
fig.subplots_adjust(left=0.07, right=0.86, top=0.915, bottom=0.055, hspace=0.42)

cmap_seq = LinearSegmentedColormap.from_list("blues", SEQ)
cmap_seq.set_bad(NEUTRAL)
VMIN, VMAX = 100, 30000

def sky(ax, m, title, sub):
    g = grid(m)
    g = np.ma.masked_where(g <= 0, g)
    ax.set_facecolor(NEUTRAL)
    im = ax.pcolormesh(ra_edges, dec_edges, g, cmap=cmap_seq,
                       norm=LogNorm(vmin=VMIN, vmax=VMAX), shading="flat",
                       rasterized=True)
    style(ax, title, sub)
    return im

def style(ax, title, sub):
    ax.set_xlim(360, 0); ax.set_ylim(-90, 90)
    ax.set_xticks(np.arange(0, 361, 60)); ax.set_yticks(np.arange(-90, 91, 30))
    ax.set_xlabel("RA [deg]", color=INK2, fontsize=9)
    ax.set_ylabel("Dec [deg]", color=INK2, fontsize=9)
    ax.tick_params(colors=INK2, labelsize=8.5, length=3)
    for s in ax.spines.values():
        s.set_color(GRID); s.set_linewidth(0.8)
    ax.grid(True, color=GRID, lw=0.4, alpha=0.5)
    # AR the declination the problems were reported at
    ax.axhline(-30, color=INK, lw=1.6, ls=(0, (5, 3)), alpha=0.85, zorder=5)
    ax.text(356, -30 + 3.5, "Dec = −30", color=INK, fontsize=8.5,
            va="bottom", ha="left", zorder=6)
    ax.set_title(title, color=INK, fontsize=12.5, fontweight="bold",
                 loc="left", pad=22)
    ax.text(0.0, 1.018, sub, transform=ax.transAxes, color=INK2,
            fontsize=9, va="bottom", ha="left")

im = sky(axes[0], maps["cmx_any"],
         "CMX path  —  fba_cmx_new",
         "STD_DITHER (in footprint) or STD_DITHER_GAIA (supp), dr9/0.49.0 + gaiadr2/0.49.0")
sky(axes[1], maps["main"],
    "Main path  —  fba_main_dither --stdsource gaia",
    "GAIA_STD_FAINT, gaiadr2/1.0.0 backup")

cax = fig.add_axes([0.875, 0.455, 0.013, 0.40])
cb = fig.colorbar(im, cax=cax)
cb.set_label("dither targets per tile (8 deg$^2$)", color=INK2, fontsize=9)
cb.ax.tick_params(colors=INK2, labelsize=8.5, length=3)
cb.outline.set_edgecolor(GRID)

# --- panel 3: which script ------------------------------------------------
ok_cmx  = maps["cmx_any"] >= USABLE
ok_main = maps["main"]    >= USABLE
cls = np.zeros(len(ok_cmx), dtype=int)      # 0 neither
cls[ok_cmx & ok_main] = 1
cls[ok_cmx & ~ok_main] = 2
cls[~ok_cmx & ok_main] = 3

cmap_cat = ListedColormap([NEUTRAL, CAT["both"], CAT["cmx"], CAT["main"]])
axes[2].set_facecolor(NEUTRAL)
axes[2].pcolormesh(ra_edges, dec_edges, grid(cls.astype(float)), cmap=cmap_cat,
                   norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], 4),
                   shading="flat", rasterized=True)
style(axes[2], "Which script to use",
      "a path counts as usable at ≥ %d dither targets per tile" % USABLE)

frac = {k: 100.0 * (cls == v).mean() for k, v in
        (("neither", 0), ("both", 1), ("cmx", 2), ("main", 3))}
axes[2].legend(handles=[
    Patch(facecolor=CAT["both"], label="either works  (%.0f%% of sky)" % frac["both"]),
    Patch(facecolor=CAT["cmx"],  label="CMX only  (%.0f%%)" % frac["cmx"]),
    Patch(facecolor=CAT["main"], label="main only  (%.0f%%)" % frac["main"]),
    Patch(facecolor=NEUTRAL, edgecolor=GRID, label="neither  (%.0f%%)" % frac["neither"]),
], loc="upper left", bbox_to_anchor=(1.005, 1.0), frameon=False,
   fontsize=9, labelcolor=INK2, handlelength=1.2, handleheight=1.2)

fig.suptitle("Dither target coverage: CMX vs main survey catalogs",
             color=INK, fontsize=14.5, fontweight="bold", x=0.07, ha="left", y=0.982)
fig.savefig("skymap/dither_coverage.png", dpi=170, facecolor=SURFACE,
            bbox_inches="tight")
print("wrote skymap/dither_coverage.png")

# --- the numbers behind the picture ---------------------------------------
print("\nsky fractions: " + "  ".join("%s=%.1f%%" % (k, v) for k, v in frac.items()))
print("\nby declination band (fraction of band usable):")
print("%-14s %10s %10s %10s" % ("Dec band", "CMX", "main", "either"))
theta, phi = hp.pix2ang(NSIDE, np.arange(len(cls)))
pdec = 90.0 - np.degrees(theta)
for lo, hi in [(-90,-60),(-60,-40),(-40,-30),(-35,-25),(-30,-20),(-20,0),(0,20),(20,40),(40,90)]:
    m = (pdec >= lo) & (pdec < hi)
    if m.sum() == 0:
        continue
    print("%-14s %9.0f%% %9.0f%% %9.0f%%" % (
        "%+d to %+d" % (lo, hi), 100*ok_cmx[m].mean(), 100*ok_main[m].mean(),
        100*(ok_cmx | ok_main)[m].mean()))
