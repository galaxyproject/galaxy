import os
import sys

from db_shell import *  # noqa
from sqlalchemy import MetaData
from sqlalchemy.orm import class_mapper

try:
    from sqlalchemy_schemadisplay import (
        create_schema_graph,
        create_uml_graph,
    )
except ImportError:
    print("please install sqlalchemy_schemadisplay to use this script (pip install sqlalchemy_schemadisplay)")
    raise


gxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(1, os.path.abspath(os.path.join(gxy_root, "lib")))

from galaxy import model

if __name__ == "__main__":
    gxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    sqlitedb = os.path.join(gxy_root, "database/universe.sqlite")
    # Try to build a representation of what's in the sqlite database
    if os.path.exists(sqlitedb):
        graph = create_schema_graph(
            metadata=MetaData("sqlite:///" + sqlitedb),
            show_datatypes=False,
            show_indexes=False,
            rankdir="LR",
            concentrate=False,
        )
        print(f"Writing galaxy_universe.png, built from {sqlitedb}")
        graph.write_png("galaxy_universe.png")
    else:
        print(f"No sqlitedb available at {sqlitedb}, skipping rendering")

    # Build UML graph from loaded mapper
    mappers = []
    for attr in dir(model):
        if attr[0] == "_":
            continue
        try:
            cls = getattr(model, attr)
            mappers.append(class_mapper(cls))
        except Exception:
            pass

    graph = create_uml_graph(
        mappers,
        show_operations=False,
    )
    print("Writing galaxy_uml.png")
    graph.write_png("galaxy_uml.png")  # write out the file
