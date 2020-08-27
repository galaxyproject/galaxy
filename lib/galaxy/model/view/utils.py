"""
View wrappers, currently using sqlalchemy_views
"""
from inspect import getmembers

from sqlalchemy.ext import compiler
from sqlalchemy_utils import view


class View:
    is_view = True


class DropView(view.DropView):
    def __init__(self, ViewModel, **kwargs):
        super().__init__(str(ViewModel.__table__.name), **kwargs)


@compiler.compiles(DropView, "sqlite")
def compile_drop_materialized_view(element, compiler, **kw):
    # modified because sqlalchemy_utils adds a cascade for
    # sqlite even though sqlite does not support cascade keyword
    return 'DROP {}VIEW IF EXISTS {}'.format(
        'MATERIALIZED ' if element.materialized else '',
        element.name
    )


class CreateView(view.CreateView):
    def __init__(self, ViewModel, **kwargs):
        super().__init__(str(ViewModel.__table__.name), ViewModel.__view__, **kwargs)


def is_view_model(o):
    return hasattr(o, '__view__') and issubclass(o, View)


def install_views(engine):
    import galaxy.model.view
    views = getmembers(galaxy.model.view, is_view_model)
    for (name, ViewModel) in views:
        # adding DropView here because our unit-testing calls this function when
        # it mocks the app and CreateView will attempt to rebuild an existing
        # view in a database that is already made, the right answer is probably
        # to change the sql that gest emitted when CreateView is rendered.
        engine.execute(DropView(ViewModel))
        engine.execute(CreateView(ViewModel))
