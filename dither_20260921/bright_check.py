import numpy as np, os
from astropy.table import Table
from desitarget.io import read_targets_in_tiles
from desitarget.targetmask import mws_mask

CEN=[(336.,30.),(0.,30.),(15.,30.),(35.,30.),(46.,2.)]
bkp="/global/cfs/cdirs/desi/target/catalogs/gaiadr2/1.0.0/targets/main/resolve/backup"

print("%-14s %7s %7s %7s %7s %7s %7s"%("centre","FAINT","BRIGHT","both","union","WD","allGaia"))
rows=[]
for ra,dec in CEN:
    t=Table(); t["TILEID"]=[1]; t["RA"]=[ra]; t["DEC"]=[dec]
    t["OBSCONDITIONS"]=[3]; t["IN_DESI"]=[1]; t["PROGRAM"]=["DARK"]
    b=read_targets_in_tiles(bkp,tiles=t,quick=True)
    f=(b["MWS_TARGET"]&mws_mask["GAIA_STD_FAINT"])>0
    br=(b["MWS_TARGET"]&mws_mask["GAIA_STD_BRIGHT"])>0
    wd=(b["MWS_TARGET"]&mws_mask["GAIA_STD_WD"])>0
    print("%-14s %7d %7d %7d %7d %7d %7d"%("%g %+g"%(ra,dec),f.sum(),br.sum(),
          (f&br).sum(),(f|br).sum(),wd.sum(),len(b)))
    rows.append((ra,dec,b,f,br))

print("\nGaia G magnitude distribution (percent of each selection)")
edges=[10,12,14,15,16,17,18,19,20,25]
print("%-14s %-8s"%("centre","sel")+"".join("%8s"%("%g-%g"%(edges[i],edges[i+1])) for i in range(len(edges)-1)))
for ra,dec,b,f,br in rows:
    g=b["GAIA_PHOT_G_MEAN_MAG"]
    for nm,sel in [("FAINT",f),("BRIGHT",br)]:
        h,_=np.histogram(g[sel],bins=edges)
        print("%-14s %-8s"%("%g %+g"%(ra,dec),nm)+"".join("%8.1f"%(100*x/max(sel.sum(),1)) for x in h))

print("\nmedian/min/max G per selection")
for ra,dec,b,f,br in rows:
    g=b["GAIA_PHOT_G_MEAN_MAG"]
    for nm,sel in [("FAINT",f),("BRIGHT",br)]:
        print("%-14s %-8s n=%5d  min=%5.2f med=%5.2f max=%5.2f"%(
            "%g %+g"%(ra,dec),nm,sel.sum(),g[sel].min(),np.median(g[sel]),g[sel].max()))
