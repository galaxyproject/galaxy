"""
View wrappers, currently using sqlalchemy_views
"""
from inspect import getmembers

import sqlalchemy_views
from sqlalchemy import Table
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.ddl import DropTable


class View(Table):
    is_view = True


class DropView(sqlalchemy_views.DropView):
    def __init__(self, view, **kwargs):
        super().__init__(view.__view__, **kwargs)


class CreateView(sqlalchemy_views.CreateView):
    def __init__(self, view, **kwargs):
        super().__init__(view.__view__, view.__definition__, **kwargs)


@compiles(DropTable, "postgresql")
def _compile_drop_table(element, compiler, **kwargs):
    if hasattr(element.element, 'is_view') and element.element.is_view:
        return compiler.visit_drop_view(element)
    return compiler.visit_drop_table(element) + ' CASCADE'


def install_views(engine):
    import galaxy.model.view
    views = getmembers(galaxy.model.view, is_view_model)
    for (name, view) in views:
        engine.execute(CreateView(view))


def is_view_model(o):
    return hasattr(o, '__view__') and isinstance(o.__view__, View)
