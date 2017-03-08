# -*- coding: utf-8 -*-

# Copyright (c) 2016 by University of Kassel and Fraunhofer Institute for Wind Energy and Energy
# System Technology (IWES), Kassel. All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.

import numpy as np
import networkx as nx

from pypower.idx_bus import BUS_I, GS, BS
from pypower.idx_brch import F_BUS, T_BUS, BR_R, BR_X


def calc_kappa(net):
    network_structure = net._options_sc["network_structure"]
    net.bus["kappa_korr"] = 1.
    if network_structure == "meshed":
        net.bus["kappa_korr"] = 1.15
    elif network_structure == "auto":
        mg = nxgraph_from_ppc(net._ppc)
        for bus in net._is_elems["bus"].index:
            ppc_index = net._pd2ppc_lookups["bus"][bus]
            paths = list(nx.all_simple_paths(mg, ppc_index, "earth"))
            if len(paths) > 1:
                net.bus.kappa_korr.at[bus] = 1.15
                for path in paths:
                    r = sum([mg[b1][b2][0]["r"] for b1, b2 in zip(path, path[1:])])
                    x = sum([mg[b1][b2][0]["x"] for b1, b2 in zip(path, path[1:])])
                    if r / x < .3:                                     
                        net.bus.kappa_korr.at[bus] = 1.
                        break           
    rx_equiv = np.real(net.bus.z_equiv) / np.imag(net.bus.z_equiv)
    kappa = 1.02 + .98 * np.exp(-3 * rx_equiv)
    net.bus["kappa"] = np.clip(net.bus.kappa_korr * kappa, 1, net.bus.kappa_max)
    
def nxgraph_from_ppc(ppc):
    mg = nx.MultiGraph()
    mg.add_nodes_from(ppc["bus"][:, 0].astype(int))
    mg.add_edges_from((int(branch[T_BUS]), int(branch[F_BUS]),
                       {"r": branch[BR_R], "x": branch[BR_X]}) for branch in ppc["branch"].real)
    mg.add_node("earth")
    voltage_sources = ppc["bus"][(ppc["bus"][:, GS] > 0) | (ppc["bus"][:, BS] > 0)]
    z = 1 / (voltage_sources[:, GS] + voltage_sources[:, BS] * 1j)
    mg.add_edges_from(("earth", int(bus), {"r": z.real, "x": z.imag}) 
                        for bus, z in zip(voltage_sources[BUS_I], z))
    return mg

