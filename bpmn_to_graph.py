import argparse
from xml.dom.minidom import parse, Document

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


def get_text(node):
    rc = []
    for node in node.childNodes:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return "".join(rc).strip()


def bpmn_to_graph(root_dom: Document):
    start_node = root_dom.getElementsByTagName("startEvent")[0]
    end_node = root_dom.getElementsByTagName("endEvent")[0]
    task_nodes = root_dom.getElementsByTagName("userTask")
    seq_flows = root_dom.getElementsByTagName("sequenceFlow")
    par_gateways = root_dom.getElementsByTagName("parallelGateway")
    exc_gateways = root_dom.getElementsByTagName("exclusiveGateway")

    node_list = [start_node, end_node] + task_nodes + par_gateways + exc_gateways

    seq_flow_ids = []
    par_gateway_ids = []
    exc_gateway_ids = []

    G = nx.DiGraph()
    for node in node_list + seq_flows:
        node_type = node.tagName
        node_id = node.getAttribute("id")
        node_name = node.getAttribute("name")

        if node_type == "sequenceFlow":
            seq_flow_ids.append(node_id)
        elif node_type == "parallelGateway":
            par_gateway_ids.append(node_id)
        elif node_type == "exclusiveGateway":
            exc_gateway_ids.append(node_id)

        G.add_node(node_id, type=node_type, name=node_name)

    for node in node_list:
        node_id = node.getAttribute("id")

        for child in node.childNodes:
            if child.nodeType == child.TEXT_NODE:
                continue
            assert child.tagName in ["incoming", "outgoing"]
            child_id = get_text(child)
            if child.tagName == "incoming":
                G.add_edge(child_id, node_id)
            elif child.tagName == "outgoing":
                G.add_edge(node_id, child_id)

    for node_id in seq_flow_ids + exc_gateway_ids:
        for predecessor in G.predecessors(node_id):
            for successor in G.successors(node_id):
                G.add_edge(predecessor, successor)

        G.remove_node(node_id)

    for node_id in par_gateway_ids:
        for predecessor in G.predecessors(node_id):
            for successor in G.successors(node_id):
                G.add_edge(predecessor, successor, is_par=True)

        G.remove_node(node_id)

    H = G.copy()

    for (u, v), lca in nx.all_pairs_lowest_common_ancestor(G):
        if u == lca or v == lca:
            continue

        ok_u = False
        for path in nx.all_simple_paths(G, lca, u):
            if len(path) > 0:
                attrs = G.get_edge_data(path[0], path[1])
                if "is_par" in attrs and attrs["is_par"]:
                    ok_u = True

        ok_v = False
        for path in nx.all_simple_paths(G, lca, v):
            if len(path) > 0:
                attrs = G.get_edge_data(path[0], path[1])
                if "is_par" in attrs and attrs["is_par"]:
                    ok_v = True

        if ok_u and ok_v:
            H.add_edge(u, v)
            H.add_edge(v, u)
            # print("add", u, v)

    return H


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bpmn", type=str)
    parser.add_argument("--out", type=str, default="adj_matrix.npy")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    root_dom = parse(args.bpmn)
    G = bpmn_to_graph(root_dom)

    adj_matrix = np.asarray(nx.adjacency_matrix(G).todense())
    np.save(args.out, adj_matrix)

    if args.show:
        nx.draw(G, with_labels=True)
        plt.show()


if __name__ == "__main__":
    main()
