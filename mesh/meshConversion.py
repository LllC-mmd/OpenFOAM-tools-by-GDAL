'''
This Python file contains functions for meshing file conversion:
[1] cad2poly
Convert points' information from AutoCAD DataExtraction command
to Triangle's .poly file for meshing
Actually, only the coordinates of points in polyline are required
[2] poly2msh
'''
import pandas as pd
import numpy as np
import networkx as nx
import random
import re
from shapely.geometry import Polygon, Point


# split one line by spaces
def space_split(s):
    s_split = re.split(r"\s+", s.strip())
    return s_split


# A reader for Triangle's .edge, .ele, .node, .poly file
def readTriangle(file, kind):
    een_set = ["edge", "ele", "node"]
    p_set = ["poly"]
    f = open(file)
    f_lines = f.readlines()
    if kind in een_set:
        # total number of edge, elements or nodes
        num = int(re.split(r"\s+", f_lines[0])[0])
        f_slice = f_lines[1:num+1]
        f_arr = np.array(list(map(space_split, f_slice)))
        return f_arr[:, 0], f_arr[:, 1], f_arr[:, 2], f_arr[:, 3]
    elif kind in p_set:
        num = int(re.split(r"\s+", f_lines[1])[0])
        f_slice = f_lines[2:num+2]
        f_arr = np.array(list(map(space_split, f_slice)))
        return f_arr[:, 0], f_arr[:, 1], f_arr[:, 2], f_arr[:, 3]
    else:
        print("No such type")


def index_find_2d(value, array):
    i1 = np.where(array[:,0]==value[0])
    i2 = np.where(array[:,1]==value[1])
    a = np.intersect1d(i1, i2)
    if len(a) > 0:
        return a[0]
    else:
        return -1


def zid_1d(i, outer_set, inner_set):
    if i in outer_set:
        return 1
    elif i in inner_set:
        return 2
    else:
        return 3


def zid_2d(xy, outer_set):
    if all(i in outer_set for i in xy):
        return 1
    else:
        return 2


def cad2poly(pt_addr, save_addr, bd_marker=1):
    '''
    Parameters
    ----------
    pt_addr : the address of point information .csv file
    save : the address to save Triangle's .poly file
    bd_marker: the total number of boundary markers
    '''
    pt_df = pd.read_csv(pt_addr)
    # count the number of segements
    sg_num = len(pt_df["端点 X"])
    # count the number of vertices
    end_pt = np.array(list(zip(pt_df["端点 X"], pt_df["端点 Y"])))
    start_pt = np.array(list(zip(pt_df["起点 X"], pt_df["起点 Y"])))
    pt_set = np.unique(np.concatenate([end_pt, start_pt]), axis=0)
    pt_num = len(pt_set)
    # divide the mesh region into different zones which are marked separately
    # [1] construct a graph of the mesh region by specifying edge-point relationship
    s_list = []
    e_list = []
    for i in range(1, sg_num + 1):
        pt_sx = pt_df["端点 X"].iloc[i - 1]
        pt_sy = pt_df["端点 Y"].iloc[i - 1]
        pt_ex = pt_df["起点 X"].iloc[i - 1]
        pt_ey = pt_df["起点 Y"].iloc[i - 1]
        s_index = index_find_2d(value=[pt_sx, pt_sy], array=pt_set) + 1
        e_index = index_find_2d(value=[pt_ex, pt_ey], array=pt_set) + 1
        if s_index == 0:
            print("Start point not found")
            continue
        elif e_index == 0:
            print("End point not found")
            continue
        else:
            s_list.append(s_index)
            e_list.append(e_index)
    edge_list = list(zip(s_list, e_list))
    # [2] use the package network to find cycle basis in the undirected graph
    # which gives nodes' index of outer edges and inner edges
    poly_G = nx.Graph(edge_list)
    poly_set = nx.cycle_basis(poly_G)
    # get the outer boundary by assuming it has the most nodes
    obd_index = np.argmax(list(map(len, poly_set)))
    outer_node = set(poly_set[obd_index])
    poly_set.pop(obd_index)  # inner boundary
    inner_node = set(sum(poly_set, []))
    # [3] determine the zone id of nodes
    # outer node:1, inner node:2, mid_fluid:3
    node_zid = [zid_1d(i, outer_set=outer_node, inner_set=inner_node) for i in list(range(1, pt_num+1))]
    # [4] determine the zone id of segements
    sg_zid = [zid_2d(edge_list[i], outer_set=outer_node) for i in list(range(0, sg_num))]
    # Writing .poly file
    # create the output file
    poly_file = open(save_addr, mode="a")
    # write summary for vertices
    poly_file.write("# Part of vertices\n")
    poly_file.write(str(pt_num)+" 2 0 0 "+str(bd_marker)+"\n")
    # write vertex i
    for i in range(1, pt_num+1):
        poly_file.write(str(i)+" "+" ".join(map(str, pt_set[i-1]))+" "+str(node_zid[i-1])+"\n")
    # write summary for segements
    poly_file.write("# Part of segements\n")
    poly_file.write(str(sg_num)+" 0 "+str(bd_marker)+"\n")
    print("The number of segements is "+str(sg_num))
    # write segement i
    for i in range(1, sg_num+1):
        poly_file.write(str(i)+" "+str(s_list[i-1])+" "+str(e_list[i-1])+" "+str(sg_zid[i-1])+"\n")
    # write summary for holes
    hole_num = len(poly_set)
    poly_file.write("# Part of holes\n")
    poly_file.write(str(hole_num)+"\n")
    print("The number of holes is " + str(hole_num))
    # write hole i with an inner point for the polygon
    h_count = 1
    for p in poly_set:
        p_i = [pt_set[i-1] for i in p]
        polygon_i = Polygon(p_i)
        while True:
            test_sample = random.sample(p_i,3)
            test_centroid = np.average(test_sample, axis=0)
            if polygon_i.contains(Point(test_centroid)):
                poly_file.write(str(h_count)+" "+" ".join(map(str, test_centroid))+"\n")
                break
        h_count += 1


def poly2msh(node_addr, poly_addr, ele_addr, save_addr):
    node_i, node_x, node_y, node_marker = readTriangle(file=node_addr, kind="node")
    poly_i, poly_s, poly_e, poly_marker = readTriangle(file=poly_addr, kind="poly")
    ele_i, ele_n1, ele_n2, ele_n3 = readTriangle(file=ele_addr, kind="ele")
    msh_file = open(save_addr, mode="a")
    # Dimension
    msh_file.write("(2 2)\n")
    # Nodes
    msh_file.write("(10 (0 1 "+format(32,"x")+" 0))\n")
    # Nodes on outer boundary ~ Zone id = 1
    # zone id: 2, inner boundary
    # zone id: 3, fluid
    msh_file.write("(10 (1 1 "+format(32,"x")+" 0))\n")
