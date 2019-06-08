# get the runoff coefficient of OpenFOAM cell centers according to landcover
from osgeo import gdal
from itertools import islice
import struct
import re


fmttypes = {'Byte':'B', 'UInt16':'H', 'Int16':'h', 'UInt32':'I', 'Int32':'i', 'Float32':'f', 'Float64':'d'}


def get_runcoeff(lc, p, dest):
    '''
    lc: the address the landcover tiff is stored in
    p: the address the OpenFOAM cell center file is stored in
    (cell center file can be extracted by OpenFOAM function)
    dest: the directory address the output runoff coeff stored in
    '''
    lc = gdal.Open(lc)
    gt = lc.GetGeoTransform()
    rb = lc.GetRasterBand(1)
    p_file = open(file=p)
    output_file = open(file=dest+"/alpha.txt", mode="a")
    p_lines = p_file.readlines()
    for line in islice(p_lines, 22, None):
        if line[0] == ")":
            break
        else:
            data = re.split(r"[\(\)]", line)
            data = re.split(r"\s", data[1])
            del(data[-1])
            mx = float(data[0])
            my = float(data[1])
            # Convert from map to pixel coordinates.
            # Only works for geotransforms with no rotation.
            px = int((mx - gt[0]) / gt[1])  # x pixel
            py = int((my - gt[3]) / gt[5])  # y pixel
            structval = rb.ReadRaster(px, py, 1, 1, buf_type=rb.DataType)
            bandtype = gdal.GetDataTypeName(rb.DataType)
            intval = struct.unpack(fmttypes[bandtype], structval)
            if intval[0] == 10:
                output_file.write("0.4\n")
            elif intval[0] == 20:
                output_file.write("0.2\n")
            elif intval[0] == 30:
                output_file.write("0.2\n")
            elif intval[0] == 50:
                output_file.write("0.2\n")
            elif intval[0] == 60:
                output_file.write("1\n")
            elif intval[0] == 90:
                output_file.write("0.6\n")
            else:
                output_file.write("1\n")
    p_file.close()
    output_file.close()


lc_file = "tiff/lc_case.tif"
p_file = "case_10m/center"
get_runcoeff(lc=lc_file, p=p_file, dest="case_10m")
