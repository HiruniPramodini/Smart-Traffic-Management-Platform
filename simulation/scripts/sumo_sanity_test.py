"""
sumo_sanity_test.py
=====================
Builds the smallest possible SUMO scenario (2 nodes, 1 edge, 1 flow)
from scratch, compiles it, runs it, and reports whether any vehicles
were inserted. This has nothing to do with your Kaduwela project --
it exists purely to answer one question: does vehicle insertion work
on this SUMO install at all?

Run from anywhere (uses a temp folder):
    python sumo_sanity_test.py
"""
import os
import subprocess
import tempfile
import sys

NOD = """<?xml version="1.0" encoding="UTF-8"?>
<nodes>
    <node id="A" x="0" y="0" type="priority"/>
    <node id="B" x="500" y="0" type="priority"/>
</nodes>
"""

EDG = """<?xml version="1.0" encoding="UTF-8"?>
<edges>
    <edge id="AB" from="A" to="B" numLanes="1" speed="13.89"/>
</edges>
"""

ROU = """<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="4.5" maxSpeed="13.89"/>
    <route id="r0" edges="AB"/>
    <flow id="f0" route="r0" type="car" begin="0" end="600" vehsPerHour="300"/>
</routes>
"""

CFG = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="test.net.xml"/>
        <route-files value="test.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="600"/>
    </time>
</configuration>
"""