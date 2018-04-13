"""
Utility helpers related to the model
"""

def pgcalc(sa_session, id, dryrun=False):
    """
    Utility method for quickly recalculating user disk usage in postgres.

    TODO: Check against the recently updated versions of sqlalchemy if this
    'special' postgresql version is even necessary.
    """
    ids_dict = {}
    total = 0
    deleted = 0
    query_history = """SELECT id, deleted
                    FROM history
                        WHERE user_id = :id
                            AND purged = false;"""
    for history_id, history_deleted in sa_session.execute(query_history, {'id': id}).fetchall():
        query_hda_dataset = """SELECT hda.deleted, d.id, d.deleted, d.total_size
                    FROM history_dataset_association hda
                        JOIN dataset d ON hda.dataset_id = d.id
                            WHERE hda.history_id = :history_id
                                AND hda.purged = false
                                AND d.purged = false
                                AND d.id NOT IN (SELECT dataset_id
                                                 FROM library_dataset_dataset_association);"""
        for hda_deleted, dataset_id, dataset_deleted, dataset_total_size in sa_session.execute(query_hda_dataset, {'history_id': history_id}).fetchall():
            if str(dataset_id) not in ids_dict:
                    total += dataset_total_size
            deleted_count = User.count_toward_deleted_disk_usage(
                dataset_id,
                history_deleted,
                hda_deleted,
                dataset_deleted,
                dataset_total_size,
                **ids_dict)
            deleted += deleted_count
    if not dryrun:
        sql_update = """UPDATE galaxy_user
                    SET disk_usage = (%s), deleted_disk_usage = (%s)
                    WHERE id = :id;""" % (total, deleted)
        sa_session.execute(sql_update, {'id': id})
    return (total, deleted)