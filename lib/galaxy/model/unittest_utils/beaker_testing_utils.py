from sqlalchemy import (
    MetaData,
    select,
    Table,
)

from galaxy.model.unittest_utils.model_testing_utils import disposing_engine


def is_cache_empty(url: str, namespace: str, beaker_table: str = "beaker_cache") -> bool:
    """Check if there are any entries for a given namespace in a beaker cache db table"""
    with disposing_engine(url) as eng:  # type: ignore[arg-type]
        metadata_obj = MetaData()
        table = Table(beaker_table, metadata_obj, autoload_with=eng)
        with eng.connect() as conn:
            result = conn.execute(select(table).where(table.c.namespace == namespace))
            return result.fetchone() is None
