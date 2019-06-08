# split OpenFOAM mesh file to face and point files
import re
from itertools import islice


def foam_to_txt(src, dest):
    # open existing foam point file
    p_file = open(file=src+"/points.txt")
    point_file = open(file=dest+"/point.txt", mode="a")
    p_lines = p_file.readlines()
    for line in islice(p_lines, 20, None):
        if line[0] == ")":
            break
        else:
            data = re.split(r"[\(\)]", line)
            data = re.split(r"\s", data[1])
            del(data[-1])
            data = " ".join(data)
            point_file.write(data)
            point_file.write("\n")
    p_file.close()
    point_file.close()

    f_file = open(file=src+"/faces.txt")
    face_3_file = open(file=dest+"/face_3.txt", mode="a")
    face_4_file = open(file=dest+"/face_4.txt", mode="a")
    f_lines = f_file.readlines()
    for line in islice(f_lines, 20, None):
        if line[0] == ")":
            break
        else:
            data = re.split(r"[\(\)]", line)
            lin = re.split(r"\s", data[1])
            l = len(lin)
            lin.append(lin[0])
            lin = " ".join(lin)
            if l == 3:
                face_3_file.write(lin)
                face_3_file.write("\n")
            elif l == 4:
                face_4_file.write(lin)
                face_4_file.write("\n")
            else:
                continue
    f_file.close()
    face_3_file.close()
    face_4_file.close()


foam_to_txt(src="case_10m", dest="case_10m")
