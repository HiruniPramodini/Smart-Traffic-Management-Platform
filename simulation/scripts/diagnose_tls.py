"""
diagnose_tls.py
=================
Steps into a running simulation via TraCI and reports, for the given
traffic light: every program SUMO knows about, which one is
currently ACTIVE, and what the signal state looks like over the
first couple minutes. This tells us directly whether the
"green_wave" program is even running, or if something else is.

Usage:
    python diagnose_tls.py ..\\kaduwela\\kaduwela.sumocfg kaduwela_center
"""


import sys
import os

def main():
    if len(sys.argv) < 3:
        sys.exit("Usage: python diagnose_tls.py <sumocfg> <tls_id>")
    sumocfg, tls_id = sys.argv[1], sys.argv[2]

    sumo_home = os.environ.get("SUMO_HOME", "")
    if sumo_home:
        tools = os.path.join(sumo_home, "tools")
        if tools not in sys.path:
            sys.path.append(tools)
    import traci

    traci.start(["sumo", "-c", sumocfg, "--no-warnings", "true"])

    all_ids = traci.trafficlight.getIDList()
    print("All traffic light IDs SUMO knows about:", all_ids)

    if tls_id not in all_ids:
        print(f"'{tls_id}' NOT in that list -- your --tls-id doesn't match. Use one from above.")
        traci.close()
        return

    programs = traci.trafficlight.getAllProgramLogics(tls_id)
    print(f"\nPrograms defined for '{tls_id}':")
    for p in programs:
        print(f"  programID={p.programID!r}  n_phases={len(p.phases)}")
        for i, ph in enumerate(p.phases):
            greens = ph.state.count("G") + ph.state.count("g")
            print(f"    phase {i}: duration={ph.duration:>5}  state={ph.state}  (green count: {greens})")

    active = traci.trafficlight.getProgram(tls_id)
    print(f"\nACTIVE program right now: {active!r}")

    print("\nStepping 120s and sampling signal state + vehicle count every 20s:")
    for _ in range(6):
        for _ in range(20):
            traci.simulationStep()
        state = traci.trafficlight.getRedYellowGreenState(tls_id)
        n_veh = traci.vehicle.getIDCount()
        t = traci.simulation.getTime()
        print(f"  t={t:>6.0f}  active_program={traci.trafficlight.getProgram(tls_id)!r}  "
              f"state={state}  vehicles_in_sim={n_veh}")

    traci.close()


if __name__ == "__main__":
    main()