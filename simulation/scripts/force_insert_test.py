"""
force_insert_test.py
======================
Tries to manually insert a single vehicle via TraCI (bypassing the
<flow> scheduling layer entirely) and reports the exact error SUMO
gives if it fails. This should tell us definitively WHY insertion
isn't happening.

Usage:
    python force_insert_test.py ..\\kaduwela\\kaduwela.sumocfg ranala_to_malabe car
"""

import sys
import os


def main():
    if len(sys.argv) < 4:
        sys.exit("Usage: python force_insert_test.py <sumocfg> <route_id> <vtype_id>")
    sumocfg, route_id, vtype_id = sys.argv[1], sys.argv[2], sys.argv[3]

    sumo_home = os.environ.get("SUMO_HOME", "")
    if sumo_home:
        tools = os.path.join(sumo_home, "tools")
        if tools not in sys.path:
            sys.path.append(tools)
    import traci

    traci.start(["sumo", "-c", sumocfg, "--no-warnings", "true"])

    print("Known route IDs:", traci.route.getIDList())
    print("Known vType IDs:", traci.vehicletype.getIDList())

    if route_id not in traci.route.getIDList():
        print(f"\n'{route_id}' not found in loaded routes -- typo, or routes failed to load.")
        traci.close()
        return

    print(f"\nAttempting traci.vehicle.add('probe1', routeID='{route_id}', typeID='{vtype_id}', depart='0') ...")
    try:
        traci.vehicle.add("probe1", routeID=route_id, typeID=vtype_id, depart="0")
        print("add() call did not raise -- stepping simulation to see if it actually enters...")
        for i in range(10):
            traci.simulationStep()
            ids = traci.vehicle.getIDList()
            print(f"  step {i}: vehicles in sim = {ids}")
            if "probe1" in ids:
                pos = traci.vehicle.getPosition("probe1")
                lane = traci.vehicle.getLaneID("probe1")
                print(f"    -> probe1 inserted successfully at lane={lane} pos={pos}")
                break
        else:
            print("  probe1 never appeared in the simulation despite add() succeeding.")
            print("  Check pending count:")
            print("  Loaded but not yet departed:", traci.simulation.getMinExpectedNumber())
    except traci.exceptions.TraCIException as e:
        print(f"\n!!! TraCIException: {e}")
        print("This is the real reason -- paste this exact message back.")

        traci.close()
    
    
    if __name__ == "__main__":
        main()