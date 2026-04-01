import importlib
import sys
import types


def _install_celery_stub() -> None:
    class DummyConf(dict):
        beat_schedule = {}

        def __setattr__(self, name, value):
            self[name] = value

        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    class DummyCelery:
        def __init__(self, *args, **kwargs):
            self.conf = DummyConf()

        def autodiscover_tasks(self, *args, **kwargs):
            return None

    celery_stub = types.ModuleType("celery")
    celery_stub.Celery = DummyCelery
    celery_stub.shared_task = lambda *args, **kwargs: (lambda fn: fn)

    schedules_stub = types.ModuleType("celery.schedules")
    schedules_stub.crontab = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}

    sys.modules["celery"] = celery_stub
    sys.modules["celery.schedules"] = schedules_stub


def test_create_app_builds_fastapi_instance():
    _install_celery_stub()

    app_factory = importlib.import_module("app.app_factory")
    created = app_factory.create_app()
    assert created.title == app_factory.app.title
    assert created.version == app_factory.app.version


def test_health_route_registered():
    _install_celery_stub()

    app_factory = importlib.import_module("app.app_factory")
    paths = {route.path for route in app_factory.app.routes}
    assert "/health" in paths
