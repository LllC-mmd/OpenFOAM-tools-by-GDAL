# Form the topological relationship between SWMM gully and OpenFOAM cell
# i.e. get the number and name of gullies in one cell
import ogr
import re


def get_gully(cf_src, g_src, dest):
    # open mesh face shp file and gully shp file
    driver = ogr.GetDriverByName('ESRI Shapefile')
    face_file = driver.Open("shp/mesh_10m.shp", 0)
    f_layer = face_file.GetLayer()
    gully_file = driver.Open(g_src, 0)
    g_layer = gully_file.GetLayer()
    # set filter for gully (gully was named as "Yxx" deliberately in SWMM input file)
    g_layer.SetAttributeFilter("NAME LIKE 'Y%'")
    # create output file
    out_file = open(dest, mode="a")
    out_file.write("Num\tPoints\n")
    # open cell-face relationship txt
    cf_file = open(cf_src)
    cf_lines = cf_file.readlines()
    # iterate on all cells
    for line in cf_lines:
        data = re.split(r"[\(\)]", line)
        data = re.split(r"\s", data[1])
        del(data[-1])
        g_list = []
        g_num = 0
        # iterate on faces of one cell
        for f_index in data:
            face = f_layer.GetFeature(int(f_index))
            f_ref = face.GetGeometryRef()
            # iterate on all of gullies to tell the number of gullies which falls in the cell
            for gully in g_layer:
                g_ref = gully.GetGeometryRef()
                if g_ref.Within(f_ref):
                    g_list.append(gully.GetField("NAME"))
                    g_num += 1
            g_layer.ResetReading()
        out_file.write(str(g_num)+"\t")
        out_file.write("\t".join(i for i in g_list))
        out_file.write("\n")
    cf_file.close()
    out_file.close()


get_gully(cf_src="case_10m/cell_face.txt", g_src="shp/gully/Junctions_50N.shp", dest="case_10m/num_gully.txt")
