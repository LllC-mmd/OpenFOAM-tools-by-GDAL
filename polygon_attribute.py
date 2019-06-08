# attach OpenFOAM simulation result(s) to polygon layer's attribute(s) in ArcGIS
# and save them as pictures
import ogr
import gdal
import re
import numpy as np
import gzip
import sys


def attach_attibute(mesh, result_dir, tar_dir, n, step, unit_size, prefix, shift):   # shift = 22
    '''
    mesh: the address the ArcGIS .shp file of OpenFOAM mesh is stored in
    result_dir: the address OpenFOAM simulation result is stored in
    tar_dir: the address pictures generated by this function is stored in
    n: the total number of result file we want to process
    step: time step for result file
    unit_size: picture pixel size
    prefix: prefix for picture name
    shift: use the shift distance so that we can get the result line e.g. (x,y,z) in OpenFOAM result file directly
    '''
    # create fields for ArcGIS layers
    driver = ogr.GetDriverByName("ESRI Shapefile")
    mesh_ds = driver.Open(mesh, 1)
    mesh_layer = mesh_ds.GetLayer()
    mesh_layer.CreateField(ogr.FieldDefn("h", ogr.OFTReal))
    mesh_layer.CreateField(ogr.FieldDefn("u", ogr.OFTReal))
    mesh_layer.CreateField(ogr.FieldDefn("v", ogr.OFTReal))
    # load fc.npy to get the corresponding relationship between OpenFOAM face and cell, i.e. [face_i, cell_i]
    # Note: [face_i, cell_i] is extracted by OpenFOAM using 'const labelList& faces = mesh.cells()[celli];'
    fc = np.load("fc.npy")
    n = int(n)
    step = int(step)
    unit_size = int(unit_size)
    for i in range(1, n):
        h_result_add = result_dir + "/" + str(i*step) + "/h.gz"
        U_result_add = result_dir + "/" + str(i*step) + "/U.gz"
        zeta_file = gzip.open(h_result_add, "r")
        zeta_lines = zeta_file.readlines()
        U_file = gzip.open(U_result_add, "r")
        U_lines = U_file.readlines()
        for mesh in mesh_layer:
            face_id = mesh.GetField("id")
            cell_id = fc[int(face_id)]
            h_i = float(zeta_lines[int(cell_id + shift)])
            U_i = U_lines[int(cell_id + shift)].decode('utf-8')
            U_i = re.split(r"[\(\)]", U_i)
            U_i = re.split(r"\s", U_i[1])
            u_i = float(U_i[0])
            v_i = float(U_i[1])
            # set field value
            mesh.SetField("h", h_i*100)
            mesh.SetField("u", u_i)
            mesh.SetField("v", v_i)
            mesh_layer.SetFeature(mesh)
        mesh_layer.ResetReading()  # reset reader pointer to the beginning
        h_result_name = tar_dir + "/" + prefix + "_h_" + str(i*step) + ".tiff"
        u_result_name = tar_dir + "/" + prefix + "_u_" + str(i*step) + ".tiff"
        v_result_name = tar_dir + "/" + prefix + "_v_" + str(i*step) + ".tiff"
        # set the basic information for the output pictures
        pixelWidth = pixelHeight = unit_size
        x_min, x_max, y_min, y_max = mesh_layer.GetExtent()
        cols = int((x_max - x_min) / pixelHeight)
        rows = int((y_max - y_min) / pixelWidth)
        NoData_value = 255
        # convert h to tiff
        target_ds = gdal.GetDriverByName('GTiff').Create(h_result_name, cols, rows, 1, gdal.GDT_Float32)
        target_ds.SetGeoTransform((x_min, pixelWidth, 0, y_min, 0, pixelHeight))
        band = target_ds.GetRasterBand(1)
        band.SetNoDataValue(NoData_value)
        band.FlushCache()
        gdal.RasterizeLayer(target_ds, [1], mesh_layer, options=["ATTRIBUTE=h"])
        target_ds = None
        # convert u to tiff
        u_target_ds = gdal.GetDriverByName('GTiff').Create(u_result_name, cols, rows, 1, gdal.GDT_Float32)
        u_target_ds.SetGeoTransform((x_min, pixelWidth, 0, y_min, 0, pixelHeight))
        u_band = u_target_ds.GetRasterBand(1)
        u_band.SetNoDataValue(NoData_value)
        u_band.FlushCache()
        gdal.RasterizeLayer(u_target_ds, [1], mesh_layer, options=["ATTRIBUTE=u"])
        u_target_ds = None
        # convert v to tiff
        v_target_ds = gdal.GetDriverByName('GTiff').Create(v_result_name, cols, rows, 1, gdal.GDT_Float32)
        v_target_ds.SetGeoTransform((x_min, pixelWidth, 0, y_min, 0, pixelHeight))
        v_band = v_target_ds.GetRasterBand(1)
        v_band.SetNoDataValue(NoData_value)
        v_band.FlushCache()
        gdal.RasterizeLayer(v_target_ds, [1], mesh_layer, options=["ATTRIBUTE=v"])
        v_target_ds = None
    mesh_ds.ExecuteSQL("ALTER TABLE mesh_10m DROP COLUMN h")  # delete field by execution of SQL
    mesh_ds.ExecuteSQL("ALTER TABLE mesh_10m DROP COLUMN u")
    mesh_ds.ExecuteSQL("ALTER TABLE mesh_10m DROP COLUMN v")


attach_attibute(mesh=sys.argv[1], result_dir=sys.argv[2], tar_dir=sys.argv[3], n=sys.argv[4], step=sys.argv[5],
                unit_size=sys.argv[6], prefix=sys.argv[7], shift=22)