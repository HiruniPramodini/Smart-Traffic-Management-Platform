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