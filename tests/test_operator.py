import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_operator_imports():
    from odme.operator import assignment_operator  # noqa: F401
    from odme.operator import compress, evaluate, od_basis  # noqa: F401


def test_core_package_imports():
    import importlib, pkgutil, odme
    failed = []
    for m in pkgutil.walk_packages(odme.__path__, "odme."):
        if "examples" in m.name:
            continue
        try:
            importlib.import_module(m.name)
        except Exception as e:                      # pragma: no cover
            failed.append((m.name, str(e)))
    assert not failed, failed


if __name__ == "__main__":
    test_operator_imports(); test_core_package_imports(); print("test_operator: OK")
