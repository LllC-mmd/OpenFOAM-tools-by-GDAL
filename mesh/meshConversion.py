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
import os
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
    # outer node:1, inner node:2, mid_fluid:0 (default by Triangle)
    node_zid = [zid_1d(i, outer_set=outer_node, inner_set=inner_node) for i in list(range(1, pt_num+1))]
    # [4] determine the zone id of segements
    sg_zid = [zid_2d(edge_list[i], outer_set=outer_node) for i in list(range(0, sg_num))]
    # Writing .poly file
    # create the output file
    poly_file = open(save_addr, mode="a")
    # write summary for vertices
    poly_file.write("# Part of vertices\n")
    poly_file.write(str(pt_num)+" 2 0 "+str(bd_marker)+"\n")
    # write vertex i
    for i in range(1, pt_num+1):
        poly_file.write(str(i)+" "+" ".join(map(str, pt_set[i-1]))+" "+str(node_zid[i-1])+"\n")
    # write summary for segements
    poly_file.write("# Part of segements\n")
    poly_file.write(str(sg_num)+" "+str(bd_marker)+"\n")
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


def poly2msh(node_addr, edge_addr, ele_addr, save_addr):
    # The format of .msh can be referred to
    # http://oss.jishulink.com/upload/201609/1473134488450_msh%20file%20format.pdf
    node_id, node_x, node_y, node_marker = readTriangle(file=node_addr, kind="node")
    node_df = pd.DataFrame({"Id": node_id.astype(int), "X":node_x.astype(float),
                            "Y":node_y.astype(float), "Node_marker": node_marker.astype(int)})
    edge_id, edge_s, edge_e, edge_marker = readTriangle(file=edge_addr, kind="edge")
    edge_df = pd.DataFrame({"Id": edge_id.astype(int), "Start": edge_s.astype(int),
                            "End": edge_e.astype(int), "Edge_marker": edge_marker.astype(int)})
    _, ele_n1, ele_n2, ele_n3 = readTriangle(file=ele_addr, kind="ele")
    ele_df = pd.DataFrame({"Node1": ele_n1.astype(int), "Node2": ele_n2.astype(int), "Node3": ele_n3.astype(int)})
    # for .msh file, outer zone:1, inner zone:2, mid zone:3 (same as Triangle's, 0 for summary)
    node_mid = node_df[node_df["Node_marker"] == 0]
    node_outer = node_df[node_df["Node_marker"] == 1]
    node_inner = node_df[node_df["Node_marker"] == 2]
    edge_mid = edge_df[edge_df["Edge_marker"] == 0]
    edge_outer = edge_df[edge_df["Edge_marker"] == 1]
    edge_inner = edge_df[edge_df["Edge_marker"] == 2]
    le_mid = len(edge_mid)
    le_outer = len(edge_outer)
    le_inner = len(edge_inner)
    # However, .msh uses first_id~last_id for one zone.
    # So we need to rearrange ids of Node, Edge, Ele
    # a dictionary of nodes where (key, value) = (old_id, new_id)
    l_mid = len(node_mid)
    l_outer = len(node_outer)
    l_inner = len(node_inner)
    outer_node_dict = {o: n for (o, n) in zip(node_outer["Id"], range(1, l_outer+1))}
    inner_node_dict = {o: n for (o, n) in zip(node_inner["Id"], range(l_outer+1, l_outer+l_inner + 1))}
    mid_node_dict = {o: n for (o, n) in zip(node_mid["Id"], range(l_outer+l_inner+1, l_outer+l_inner+l_mid+1))}
    node_dict = {**outer_node_dict, **inner_node_dict, **mid_node_dict}
    # reverse dict for the above dict
    outer_node_r = {n: o for (o, n) in zip(node_outer["Id"], range(1, l_outer + 1))}
    inner_node_r = {n: o for (o, n) in zip(node_inner["Id"], range(l_outer + 1, l_outer + l_inner+1))}
    mid_node_r = {n: o for (o, n) in zip(node_mid["Id"], range(l_outer+l_inner+1, l_outer+l_inner+l_mid+1))}
    node_r = {**outer_node_r, **inner_node_r, **mid_node_r}
    # change the node index in the element_dataframe into new one
    f_on = np.vectorize(lambda x: node_dict[x])
    ele_df_new = f_on(ele_df)
    # create .msh file
    msh_file = open(save_addr, mode="a")
    # Dimension
    msh_file.write("(2 2)\n")
    # [1] Node summary
    msh_file.write("(10 (0 1 "+format(l_outer+l_inner+l_mid,"x")+" 0))\n")
    # nodes on outer boundary
    msh_file.write("(10 (1 1 "+format(l_outer,"x")+" 1 2)(\n")
    node_outer = node_outer.drop(columns=["Node_marker", "Id"])
    for i in range(0, l_outer):
        msh_file.write(" ".join(map(str, node_outer.iloc[i]))+"\n")
    msh_file.write("))\n")
    # nodes on inner boundary
    msh_file.write("(10 (2 "+format(l_outer+1, "x")+" "+format(l_outer+l_inner, "x")+" 1 2)(\n")
    node_inner = node_inner.drop(columns=["Node_marker", "Id"])
    for i in range(0, l_inner):
        msh_file.write(" ".join(map(str, node_inner.iloc[i]))+"\n")
    msh_file.write("))\n")
    # nodes in the middle
    msh_file.write("(10 (3 "+format(l_outer+l_inner+1, "x")+" "+format(l_outer+l_inner+l_mid, "x") + " 1 2)(\n")
    node_mid = node_mid.drop(columns=["Node_marker", "Id"])
    for i in range(0, l_mid):
        msh_file.write(" ".join(map(str, node_mid.iloc[i]))+"\n")
    msh_file.write("))\n")
    # [2] Face/Edge summary
    msh_file.write("(13 (0 1 "+format(le_outer+le_inner+le_mid, "x")+" 0))\n")
    # edges on outer boundary
    # for wall condition, type = 3
    msh_file.write("(13 (1 1 "+format(le_outer, "x")+" 3 2)(\n")
    edge_outer = edge_outer.drop(columns=["Edge_marker", "Id"])
    for i in range(0, le_outer):
        # find the neighbour cell
        # note that we should update the old index to the new index
        ei_se = edge_outer.iloc[i]
        ei_se_new = [node_dict[o_id] for o_id in ei_se]
        # find the cell which the edge belongs to
        f_neighbor = np.vectorize(lambda x, y, z: {ei_se_new[0], ei_se_new[1]}.issubset({x, y, z}))
        neighbor_test = f_neighbor(ele_df_new[:, 0], ele_df_new[:, 1], ele_df_new[:, 2])
        cell_id = np.where(neighbor_test)[0][0]
        # get the third node new id
        n_id = set(ele_df_new[cell_id]).difference({ei_se_new[0], ei_se_new[1]})
        neighbor_cell = node_r[list(n_id)[0]]
        # boundary edge has only one cell
        msh_file.write(" ".join(map(lambda j: format(j, "x"), ei_se_new))+" "+format(neighbor_cell, "x")+" 0\n")
    # edges on inner boundary
    msh_file.write("(13 (2 "+format(le_outer+1, "x")+" "+format(le_outer+le_inner, "x")+" 3 2)(\n")
    edge_inner = edge_inner.drop(columns=["Edge_marker", "Id"])
    for i in range(0, le_inner):
        ei_se = edge_inner.iloc[i]
        ei_se_new = [node_dict[o_id] for o_id in ei_se]
        f_neighbor = np.vectorize(lambda x, y, z: {ei_se_new[0], ei_se_new[1]}.issubset({x, y, z}))
        neighbor_test = f_neighbor(ele_df_new[:, 0], ele_df_new[:, 1], ele_df_new[:, 2])
        cell_id = np.where(neighbor_test)[0][0]
        n_id = set(ele_df_new[cell_id]).difference({ei_se_new[0], ei_se_new[1]})
        neighbor_cell = node_r[list(n_id)[0]]
        msh_file.write(" ".join(map(lambda j: format(j, "x"), ei_se_new))+" "+format(neighbor_cell, "x")+" 0\n")
    # edges in the middle
    msh_file.write("(13 (3 "+format(le_outer+le_inner+1)+" "+format(le_outer+le_inner+le_mid, "x")+" 2 2)(\n")
    edge_mid = edge_mid.drop(columns=["Edge_marker", "Id"])
    for i in range(0, le_outer):
        ei_se = edge_mid.iloc[i]
        s_i = ei_se[0]
        s_xy = np.array([node_outer["X"].iloc[s_i], node_outer["Y"].iloc[s_i]])
        e_i = ei_se[1]
        e_xy = np.array([node_outer["X"].iloc[e_i], node_outer["Y"].iloc[e_i]])
        ei_se_new = [node_dict[o_id] for o_id in ei_se]
        f_neighbor = np.vectorize(lambda x, y, z: {ei_se_new[0], ei_se_new[1]}.issubset({x, y, z}))
        neighbor_test = f_neighbor(ele_df_new[:, 0], ele_df_new[:, 1], ele_df_new[:, 2])
        cell1_id = np.where(neighbor_test)[0][0]
        n1_id = set(ele_df_new[cell1_id]).difference({ei_se_new[0], ei_se_new[1]})
        neighbor_cell_1 = node_r[list(n1_id)[0]]
        cell2_id = np.where(neighbor_test)[0][1]
        n2_id = set(ele_df_new[cell2_id]).difference({ei_se_new[0], ei_se_new[1]})
        neighbor_cell_2 = node_r[list(n2_id)[0]]
        # use cross product to verify if s_i~e_i~c1 is clockwise
        c1 = set(ele_df_new.iloc[neighbor_cell_1]).difference({s_i, e_i})
        c1_xy = np.array([node_outer["X"].iloc[c1], node_outer["Y"].iloc[c1]])
        z1_cross = np.cross(e_xy-s_xy, c1_xy-s_xy)
        if z1_cross < 0:  # s_i~e_i~c1 is clockwise
            msh_file.write(" ".join(map(lambda j: format(j, "x"), ei_se_new))+" "
                +format(neighbor_cell_1, "x")+" "+format(neighbor_cell_2, "x")+"\n")
        else:
            msh_file.write(" ".join(map(lambda j: format(j, "x"), ei_se_new))+" "
                            +format(neighbor_cell_2, "x") + " " + format(neighbor_cell_1, "x") + "\n")
    # [3] Cell summary
    l_cell = len(ele_df_new)
    msh_file.write("(12 (0 1 " + format(l_cell, "x") + " 0\n")
    msh_file.write("(12 (3 1 " + format(l_cell, "x") + " 1 0)(\n")
    for i in range(0, l_cell):
        msh_file.write("3\n")
    msh_file.write("))\n")
    # [4] Zone summary
    # outer zone
    msh_file.write("(45 (1 wall outer_boundary)())\n")
    # inner zone
    msh_file.write("(45 (2 wall inner_boundary)())\n")
    # mid zone
    msh_file.write("(45 (3 fluid mid_region)())")
 
# cad2poly(pt_addr, save_addr, bd_marker=1)
# os.system("triangle -epa100 XX.poly")
# poly2msh(node_addr, edge_addr, ele_addr, save_addr)
