"""
Migration script to add the sample_dataset table and remove the 'dataset_files' column
from the 'sample' table
"""

import datetime
import logging
from json import loads

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import localtimestamp, nextval

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()


SampleDataset_table = Table('sample_dataset', metadata,
                            Column("id", Integer, primary_key=True),
                            Column("create_time", DateTime, default=now),
                            Column("update_time", DateTime, default=now, onupdate=now),
                            Column("sample_id", Integer, ForeignKey("sample.id"), index=True),
                            Column("name", TrimmedString(255), nullable=False),
                            Column("file_path", TrimmedString(255), nullable=False),
                            Column("status", TrimmedString(255), nullable=False),
                            Column("error_msg", TEXT),
                            Column("size", TrimmedString(255)))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        SampleDataset_table.create()
    except Exception:
        log.exception("Creating sample_dataset table failed.")

    cmd = "SELECT id, dataset_files FROM sample"
    result = migrate_engine.execute(cmd)
    for r in result:
        sample_id = r[0]
        if r[1]:
            dataset_files = loads(r[1])
            for df in dataset_files:
                if isinstance(df, dict):
                    cmd = "INSERT INTO sample_dataset VALUES (%s, %s, %s, %s, '%s', '%s', '%s', '%s', '%s')"
                    cmd = cmd % (nextval(migrate_engine, 'sample_dataset'),
                                 localtimestamp(migrate_engine),
                                 localtimestamp(migrate_engine),
                                 str(sample_id),
                                 df.get('name', ''),
                                 df.get('filepath', ''),
                                 df.get('status', '').replace('"', '').replace("'", ""),
                                 "",
                                 df.get('size', '').replace('"', '').replace("'", "").replace(df.get('filepath', ''), '').strip())
                migrate_engine.execute(cmd)

    # Delete the dataset_files column in the Sample table
    try:
        Sample_table = Table("sample", metadata, autoload=True)
    except NoSuchTableError:
        Sample_table = None
        log.debug("Failed loading table sample")
    if Sample_table is not None:
        try:
            Sample_table.c.dataset_files.drop()
        except Exception:
            log.exception("Deleting column 'dataset_files' from the 'sample' table failed.")


def downgrade(migrate_engine):
    pass
