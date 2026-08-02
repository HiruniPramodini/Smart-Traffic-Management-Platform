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