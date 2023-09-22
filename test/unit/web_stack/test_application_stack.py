from gunicorn import SERVER_SOFTWARE

from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.web_stack import (
    application_stack_class,
    application_stack_instance,
    GunicornApplicationStack,
    WeblessApplicationStack,
)


def test_application_stack_class_factory(monkeypatch):
    assert application_stack_class() == WeblessApplicationStack
    monkeypatch.setenv("SERVER_SOFTWARE", SERVER_SOFTWARE)
    assert application_stack_class() == GunicornApplicationStack


def test_application_stack_instance_factory(monkeypatch):
    app = GalaxyDataTestApp()
    monkeypatch.setenv("SERVER_SOFTWARE", SERVER_SOFTWARE)
    stack_instance = application_stack_instance(app=app, config=app.config)
    assert isinstance(stack_instance, GunicornApplicationStack)
    assert stack_instance.name == "Gunicorn"


def test_application_stack_post_fork(monkeypatch):
    app = GalaxyDataTestApp()
    monkeypatch.setenv("SERVER_SOFTWARE", SERVER_SOFTWARE)
    monkeypatch.setenv("GUNICORN_WORKER_ID", "100")
    monkeypatch.setattr(GunicornApplicationStack, "do_post_fork", True)
    stack_instance = application_stack_instance(app=app, config=app.config)
    assert isinstance(stack_instance, GunicornApplicationStack)
    GunicornApplicationStack.register_postfork_function(lambda: stack_instance.set_postfork_server_name(app))
    assert not app.config.server_name.endswith(".100")
    GunicornApplicationStack.late_postfork()
    GunicornApplicationStack.late_postfork_event.set()
    GunicornApplicationStack.late_postfork_thread.join()
    assert app.config.server_name.endswith(".100")
