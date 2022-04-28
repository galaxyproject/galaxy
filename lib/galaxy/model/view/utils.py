"""
View wrappers
"""
from inspect import getmembers

from sqlalchemy import (
    Column,
    MetaData,
    Table,
)
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement


class View:
    """Base class for Views."""

    @staticmethod
    def _make_table(name, selectable, pkeys):
        """Create a view.

        :param name: The name of the view.
        :param selectable: SQLAlchemy selectable.
        :param pkeys: set of primary keys for the selectable.
        """
        columns = [Column(c.name, c.type, primary_key=(c.name in pkeys)) for c in selectable.subquery().columns]
        # We do not use the metadata object from model.mapping.py that contains all the Table objects
        # because that would create a circular import (create_view is called from View objects
        # in model.view; but those View objects are imported into model.mapping.py where the
        # metadata object we need is defined). Thus, we do not use the after_create/before_drop
        # hooks to automate creating/dropping views.  Instead, this is taken care of in install_views().

        # The metadata object passed to Table() should be empty: this table is internal to a View
        # object and is not intended to be created in the database.
        return Table(name, MetaData(), *columns)


class CreateView(DDLElement):
    def __init__(self, name, selectable):
        self.name = name
        self.selectable = selectable


class DropView(DDLElement):
    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    compiled_selectable = compiler.sql_compiler.process(element.selectable, literal_binds=True)
    return f"CREATE VIEW {element.name} AS {compiled_selectable}"


@compiler.compiles(DropView)
def compile_drop_view(element, compiler, **kw):
    return f"DROP VIEW IF EXISTS {element.name}"


def is_view_model(o):
    return hasattr(o, "__view__") and issubclass(o, View)


def install_views(engine):
    import galaxy.model.view

    views = getmembers(galaxy.model.view, is_view_model)
    for _, view in views:
        # adding DropView here because our unit-testing calls this function when
        # it mocks the app and CreateView will attempt to rebuild an existing
        # view in a database that is already made, the right answer is probably
        # to change the sql that gest emitted when CreateView is rendered.
        with engine.begin() as conn:
            conn.execute(DropView(view.name))
            conn.execute(CreateView(view.name, view.__view__))
