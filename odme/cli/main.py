"""Minimal CLI entry: print the resolved version preset (honest feature switch)."""
from __future__ import annotations
import sys
from .run_config import get_config, VERSIONS


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    ver = argv[0] if argv else None
    if ver in ("-h", "--help"):
        print("usage: python -m odme.cli.main [version]\nversions:", ", ".join(VERSIONS))
        return
    cfg = get_config(ver)
    print(f"resolved config: {cfg['version']}")
    for k, v in cfg.items():
        print(f"  {k:28} {v}")
    if cfg["queue_layer"] != "off":
        print("\nNOTE: queue layer is DIAGNOSTIC/EXPERIMENTAL -- not validated physics-informed ODME.")


if __name__ == "__main__":
    main()
