import importlib


def test_import_backend_modules():
    importlib.import_module("app.core.models")
    importlib.import_module("app.core.gedcom")
    importlib.import_module("app.api.export")
