"""
Utility helpers related to the model
"""


def pgcalc( sa_session, id, dryrun=False ):
    """
    Utility method for quickly recalculating user disk usage in postgres.

    TODO: Check against the recently updated versions of sqlalchemy if this
    'special' postgresql version is even necessary.
    """
    sql = """
           UPDATE galaxy_user
              SET disk_usage = (SELECT COALESCE(SUM(total_size), 0)
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
                                         ) sizes)
            WHERE id = :id
        RETURNING disk_usage;
    """
    r = sa_session.execute(sql, {'id': id})
    new = r.fetchone()[0]
    if dryrun:
        sa_session.rollback()
    return new
