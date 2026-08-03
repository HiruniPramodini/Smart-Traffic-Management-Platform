"""
build_green_wave_phases.py
============================
Replaces hand-written .tll.xml files with ones built from the ACTUAL
connections SUMO's netconvert generated — no guessing state-string
length or link order.

Why this exists: a traffic light's state string has exactly one
character per incoming <connection> (fromEdge/fromLane -> toEdge/toLane)
at that junction. Outgoing edges never appear in it. When an arm's
traffic can turn onto more than one other arm (as your .rou.xml files
require — every arm routes to every other arm), the number of
connections per arm depends on the lane geometry netconvert computes,
not a fixed "2 per arm" you can predict by hand.

USAGE (run AFTER netconvert has produced <junction>.net.xml, and
BEFORE writing/loading a custom .tll.xml):

    python build_green_wave_phases.py kaduwela.net.xml \
        --axis malabe:NS biyagama:NS kotikawatta:EW ranala:EW \
        --tls-id kaduwela_center \
        --out kaduwela.tll.xml \
        --offset 0

    python build_green_wave_phases.py biyagama.net.xml \
        --axis kaduwela:MAIN industrial:CROSS kelaniya:CROSS \
        --tls-id biyagama_center \
        --out biyagama.tll.xml \
        --offset 270

Group names just need to be consistent within one junction — use
NS/EW for the 4-arm hub (Kaduwela), and MAIN/CROSS for the 3-arm
junctions (the Kaduwela-facing arm gets its own phase, the other two
arms share a phase — this is what your original design intended).

After running this for all 5 junctions, point each <junction>.sumocfg's
additional-files at the newly generated .tll.xml, and keep the
traci.trafficlight.setProgram(...) safety call in
generate_7day_sumo.py so the custom program is definitely the active
one at runtime regardless of what netconvert set as default.
"""


import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict


def arm_from_edge(edge_id):
    # edge ids are "<arm>_in" / "<arm>_out" by this project's convention
    return edge_id.rsplit("_in", 1)[0] if edge_id.endswith("_in") else edge_id.rsplit("_out", 1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("net_file")
    ap.add_argument("--tls-id", required=True, help="traffic light id, e.g. kaduwela_center")
    ap.add_argument("--axis", nargs="+", required=True,
                     help="arm:GROUP pairs, e.g. malabe:NS biyagama:NS kotikawatta:EW ranala:EW")
    ap.add_argument("--out", required=True)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--green", type=int, default=45, help="green phase duration (s)")
    ap.add_argument("--yellow", type=int, default=4, help="yellow phase duration (s)")
    args = ap.parse_args()

    arm_group = dict(pair.split(":") for pair in args.axis)

