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

