"""
Migration script to create missing indexes.  Adding new columns to existing tables via SQLAlchemy does not create the index, even if the column definition includes index=True.
"""
from __future__ import print_function

import logging

from sqlalchemy import Index, MetaData, Table
from sqlalchemy.engine import reflection

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
metadata = MetaData()

indexes = (
    ( "ix_metadata_file_lda_id", 'metadata_file', 'lda_id' ),                                   # 0003
    ( "ix_history_importable", 'history', 'importable' ),                                       # 0007
    ( "ix_sample_bar_code", 'sample', 'bar_code' ),                                             # 0009
    ( "ix_request_type_deleted", 'request_type', 'deleted' ),                                   # 0012
    ( "ix_galaxy_user_username", 'galaxy_user', 'username' ),                                   # 0014
    ( "ix_form_definition_type", 'form_definition', 'type' ),                                   # 0019
    ( "ix_form_definition_layout", 'form_definition', 'layout' ),                               # 0019
    ( "ix_job_library_folder_id", 'job', 'library_folder_id' ),                                 # 0020
    ( "ix_page_published", 'page', 'published' ),                                               # 0023
    ( "ix_page_deleted", 'page', 'deleted' ),                                                   # 0023
    ( "ix_galaxy_user_form_values_id", 'galaxy_user', 'form_values_id' ),                       # 0025
    ( "ix_lia_deleted", 'library_info_association', 'deleted' ),                                # 0036
    ( "ix_lfia_deleted", 'library_folder_info_association', 'deleted' ),                        # 0036
    ( "ix_lddia_deleted", 'library_dataset_dataset_info_association', 'deleted' ),              # 0036
    ( "ix_sample_library_id", 'sample', 'library_id' ),                                         # 0037
    ( "ix_sample_folder_id", 'sample', 'folder_id' ),                                           # 0037
    ( "ix_lia_inheritable", 'library_info_association', 'inheritable' ),                        # 0038
    ( "ix_lfia_inheritable", 'library_folder_info_association', 'inheritable' ),                # 0038
    ( "ix_job_imported", 'job', 'imported' ),                                                   # 0051
    ( "ix_request_notification", 'request', 'notification' ),                                   # 0057
    ( "ix_sd_external_service_id", 'sample_dataset', 'external_service_id' ),                   # 0068
    ( "ix_icda_ldda_parent_id", 'implicitly_converted_dataset_association', 'ldda_parent_id' ),  # 0073
    ( "ix_library_dataset_purged", 'library_dataset', 'purged' ),                               # 0074
    ( "ix_run_subindex", 'run', 'subindex' ),                                                   # 0075
    ( "ix_history_dataset_association_purged", 'history_dataset_association', 'purged' ),       # 0078
    ( "ix_galaxy_user_disk_usage", 'galaxy_user', 'disk_usage' ),                               # 0078
    ( "ix_galaxy_session_disk_usage", 'galaxy_session', 'disk_usage' ),                         # 0078
    ( "ix_icda_ldda_id", 'implicitly_converted_dataset_association', 'ldda_id' ),               # 0084
    ( "ix_tsr_includes_datatypes", 'tool_shed_repository', 'includes_datatypes' ),              # 0086
    ( "ix_dataset_object_store_id", 'dataset', 'object_store_id' ),                             # 0089
    ( "ix_job_object_store_id", 'job', 'object_store_id' ),                                     # 0089
    ( "ix_metadata_file_object_store_id", 'metadata_file', 'object_store_id' ),                 # 0089
    ( "ix_job_handler", 'job', 'handler' ),                                                     # 0094
    ( "ix_galaxy_user_email", 'galaxy_user', 'email' )                                          # 0106
)


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    insp = reflection.Inspector.from_engine(migrate_engine)
    # Create missing indexes
    for ix, table, col in indexes:
        try:
            log.debug("Creating index '%s' on column '%s' in table '%s'" % (ix, col, table))
            t = Table( table, metadata, autoload=True )
            if ix not in [ins_ix.get('name', None) for ins_ix in insp.get_indexes(table)]:
                Index( ix, t.c[col] ).create()
            else:
                pass  # Index already exists, don't recreate.
        except Exception:
            log.exception("Unable to create index '%s'." % ix)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop indexes
    for ix, table, col in indexes:
        try:
            t = Table( table, metadata, autoload=True )
            Index( ix, t.c[col] ).drop()
        except Exception:
            log.exception("Unable to drop index '%s'." % ix)
