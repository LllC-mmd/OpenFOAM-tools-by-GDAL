# convert Fluent msh face to polygon layer in ArcGIS
# Fluent mesh is consisted of triangles and quadrangles
import ogr
import numpy as np


# create ArcGIS polygon according to points' coordinates
def create_polygon(unit, point_ref):
    poly = ogr.Geometry(ogr.wkbPolygon)
    ring = ogr.Geometry(ogr.wkbLinearRing)
    l = len(unit)
    for i in range(0, l):
        index = int(unit[i])
        ring.AddPoint(point_ref[index][0], point_ref[index][1])
    poly.AddGeometry(ring)
    return poly


face_3 = np.loadtxt("case_10m/face_3.txt")
face_4 = np.loadtxt("case_10m/face_4.txt", delimiter=' ')
point = np.loadtxt("case_10m/point.txt")
out_shp = r"shp/mesh_10m.shp"

driver = ogr.GetDriverByName("ESRI Shapefile")
data_source = driver.CreateDataSource(out_shp)
layer = data_source.CreateLayer("", None, ogr.wkbPolygon)
layer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
defn = layer.GetLayerDefn()

n4 = len(face_4)
n3 = len(face_3)
for i in range(0, n4):
    poly = create_polygon(unit=face_4[i], point_ref=point)
    # create a feature
    feat = ogr.Feature(defn)
    feat.SetField("id", i)
    # Make a geometry, from shape object
    geom = ogr.CreateGeometryFromWkt(poly.ExportToWkt())
    feat.SetGeometry(geom)
    layer.CreateFeature(feat)

for i in range(n4, n4+n3):
    poly = create_polygon(unit=face_3[int(i-n4)], point_ref=point)
    feat = ogr.Feature(defn)
    feat.SetField("id", i)
    geom = ogr.CreateGeometryFromWkt(poly.ExportToWkt())
    feat.SetGeometry(geom)
    layer.CreateFeature(feat)

ds = layer = feat = geom = None
