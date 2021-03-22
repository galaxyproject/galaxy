"""
View wrappers, currently using sqlalchemy_views
"""
from inspect import getmembers

from sqlalchemy import (
    Column,
    MetaData,
    Table,
    event
)
from sqlalchemy.schema import DDLElement
from sqlalchemy.ext import compiler


class View:
    is_view = True


class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


@compiler.compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    compiled_selectable = compiler.sql_compiler.process(element.selectable, literal_binds=True)
    return f'CREATE VIEW {element.name} AS {compiled_selectable}'


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


@compiler.compiles(DropView)
def compile_drop_view(element, compiler, **kw):
    return f'DROP VIEW IF EXISTS {element.name}'


def is_view_model(o):
    return hasattr(o, '__view__') and issubclass(o, View)


def install_views(engine):
    import galaxy.model.view
    views = getmembers(galaxy.model.view, is_view_model)
    for _, view in views:
        # adding DropView here because our unit-testing calls this function when
        # it mocks the app and CreateView will attempt to rebuild an existing
        # view in a database that is already made, the right answer is probably
        # to change the sql that gest emitted when CreateView is rendered.
        engine.execute(DropView(view.name))
        engine.execute(CreateView(view.name, view.__view__))


def create_view(name, selectable, pkey):
    metadata = MetaData()

    columns = [
        Column(
            c.name,
            c.type,
            primary_key=(c.name == pkey)
        )
        for c in selectable.subquery().c
    ]
    table = Table(name, metadata, *columns)

    event.listen(metadata, 'after_create', CreateView(name, selectable))
    event.listen(metadata, 'before_drop', DropView(name))

    return table

