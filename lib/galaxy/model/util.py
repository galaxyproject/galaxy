"""
Utility helpers related to the model
"""


def pgcalc(sa_session, id, dryrun=False):
    """
    Utility method for quickly recalculating user disk usage in postgres.

    TODO: Check against the recently updated versions of sqlalchemy if this
    'special' postgresql version is even necessary.
    """
    sql_calc = """SELECT COALESCE(SUM(total_size), 0)
                  FROM (  SELECT DISTINCT ON (d.id) d.total_size, d.id
                          FROM history_dataset_association hda
                               JOIN history h ON h.id = hda.history_id
                               JOIN dataset d ON hda.dataset_id = d.id
                          WHERE h.user_id = :id
                                AND h.purged = false
                                AND hda.purged = false
                                AND d.purged = false
                                AND d.id NOT IN (SELECT dataset_id
                                                 FROM library_dataset_dataset_association)
                  ) sizes"""
    sql_update = """UPDATE galaxy_user
                    SET disk_usage = (%s)
                    WHERE id = :id
                    RETURNING disk_usage;""" % sql_calc
    if dryrun:
        r = sa_session.execute(sql_calc, {'id': id})
    else:
        r = sa_session.execute(sql_update, {'id': id})
    return r.fetchone()[0]


def pgcalc_deleted(sa_session, id):
    """
    Utility method for quickly recalculating user deleted, non-purged disk usage in postgres.

    TODO: Check against the recently updated versions of sqlalchemy if this
    'special' postgresql version is even necessary.
    """
    dataset_ids = {}
    deleted_usage = 0
    query_history = """SELECT id, deleted
                    FROM history
                        WHERE user_id = :id
                            AND purged = false;"""
    for history_id, history_deleted in sa_session.execute(query_history, {'id': id}).fetchall():
        query_hda_dataset = """SELECT hda.deleted, d.id, d.deleted, d.file_size
                    FROM history_dataset_association hda
                        JOIN dataset d ON hda.dataset_id = d.id
                            WHERE hda.history_id = :history_id
                                AND hda.purged = false
                                AND d.purged = false;"""
        for hda_deleted, dataset_id, dataset_deleted, dataset_file_size in sa_session.execute(query_hda_dataset, {'history_id': history_id}).fetchall():
            query_ldda = """SELECT * FROM library_dataset_dataset_association
                            WHERE dataset_id = :dataset_id;"""
            if sa_session.execute(query_ldda, {'dataset_id': dataset_id}).fetchone():
                continue
            if str(dataset_id) in dataset_ids and (dataset_ids[str(dataset_id)] == -1 or dataset_ids[str(dataset_id)] == 3):
                continue
            if str(dataset_id) not in dataset_ids:
                if dataset_deleted:
                    dataset_ids[str(dataset_id)] = -1
                    deleted_usage += dataset_file_size
                elif hda_deleted and history_deleted:
                    dataset_ids[str(dataset_id)] = 0
                    deleted_usage += dataset_file_size
                elif not hda_deleted and history_deleted:
                    dataset_ids[str(dataset_id)] = 1
                    deleted_usage += dataset_file_size
                elif hda_deleted and not history_deleted:
                    dataset_ids[str(dataset_id)] = 2
                    deleted_usage += dataset_file_size
                else:
                    dataset_ids[str(dataset_id)] = 3
            else:
                if hda_deleted and history_deleted:
                    dataset_ids[str(dataset_id)] = dataset_ids[str(dataset_id)] | 0
                elif not hda_deleted and history_deleted:
                    dataset_ids[str(dataset_id)] = dataset_ids[str(dataset_id)] | 1
                elif hda_deleted and not history_deleted:
                    dataset_ids[str(dataset_id)] = dataset_ids[str(dataset_id)] | 2
                else:
                    dataset_ids[str(dataset_id)] = dataset_ids[str(dataset_id)] | 3
                if dataset_ids[str(dataset_id)] == 3:
                    deleted_usage -= dataset_file_size
    return deleted_usage
