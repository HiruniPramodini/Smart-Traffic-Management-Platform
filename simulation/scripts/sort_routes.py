"""
sort_routes.py
================
SUMO's route-file reader requires <vehicle>/<flow> elements to appear
sorted by begin/depart time ascending -- otherwise it silently drops
anything that arrives "in the past" relative to its read cursor. This
rewrites a .rou.xml with vType/route definitions untouched, but with
all <flow> and <vehicle> elements reordered by begin/depart time.

Usage:
    python sort_routes.py ..\\kaduwela\\kaduwela.rou.xml
    (overwrites in place; a .bak backup of the original is kept)
"""
import sys
import xml.etree.ElementTree as ET
import shutil


def depart_key(elem):
    if elem.tag == "flow":
        return float(elem.get("begin", "0"))
    return float(elem.get("depart", "0"))


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python sort_routes.py <path-to-rou.xml>")
    path = sys.argv[1]

    shutil.copy(path, path + ".bak")

    tree = ET.parse(path)
    root = tree.getroot()

    children = list(root)
    static = [c for c in children if c.tag not in ("flow", "vehicle")]
    dynamic = [c for c in children if c.tag in ("flow", "vehicle")]

    before = [(c.tag, c.get("id"), depart_key(c)) for c in dynamic]
    dynamic_sorted = sorted(dynamic, key=depart_key)

    was_sorted = [depart_key(c) for c in dynamic] == [depart_key(c) for c in dynamic_sorted]
    print(f"{path}: {len(dynamic)} flow/vehicle elements, "
          f"{'already sorted' if was_sorted else 'WAS OUT OF ORDER -- fixing'}")

    for c in children:
        root.remove(c)
    for c in static:
        root.append(c)
    for c in dynamic_sorted:
        root.append(c)

    tree.write(path, encoding="UTF-8", xml_declaration=True)
    print(f"  wrote sorted file (original backed up to {path}.bak)")

    print("  order after sort (id, begin):")
    for c in dynamic_sorted:
        print(f"    {c.get('id')}: begin={depart_key(c)}")


if __name__ == "__main__":
    main()  