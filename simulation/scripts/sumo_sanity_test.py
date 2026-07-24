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



def main():
    d = tempfile.mkdtemp(prefix="sumo_sanity_")
    print(f"Working in {d}")

    with open(os.path.join(d, "test.nod.xml"), "w", encoding="utf-8") as f:
        f.write(NOD)
    with open(os.path.join(d, "test.edg.xml"), "w", encoding="utf-8") as f:
        f.write(EDG)
    with open(os.path.join(d, "test.rou.xml"), "w", encoding="utf-8") as f:
        f.write(ROU)
    with open(os.path.join(d, "test.sumocfg"), "w", encoding="utf-8") as f:
        f.write(CFG)

    print("\n--- running netconvert ---")
    r = subprocess.run(
        ["netconvert", "--node-files", "test.nod.xml", "--edge-files", "test.edg.xml",
         "--output-file", "test.net.xml"],
        cwd=d, capture_output=True, text=True
    )
    print(r.stdout)
    print(r.stderr)
    if r.returncode != 0:
        sys.exit("netconvert failed -- SUMO install itself has a problem.")

    print("\n--- running sumo ---")
    r = subprocess.run(
        ["sumo", "-c", "test.sumocfg", "--no-step-log", "true"],
        cwd=d, capture_output=True, text=True
    )
    print(r.stdout)
    print(r.stderr)

    if "Inserted: 0" in r.stdout:
        print("\n>>> RESULT: 0 vehicles inserted even in this minimal test.")
        print(">>> This means the problem is your SUMO install/version, not your project files.")
    else:
        print("\n>>> RESULT: vehicles WERE inserted in this minimal test.")
        print(">>> This means SUMO itself works fine -- the problem is specific to")
        print(">>> something in your Kaduwela project's .rou.xml or .tll.xml files.")


if __name__ == "__main__":
    main()
