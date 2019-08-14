"""
Utility helpers related to the model
"""


def pgcalc(sa_session, id, dryrun=False):
    """
    Utility method for quickly recalculating user disk usage in postgres.

    TODO: Check against the recently updated versions of sqlalchemy if this
    'special' postgresql version is even necessary.
    """
    ctes = """
        WITH per_user_histories AS
        (
            SELECT history.id as id
            FROM history
            WHERE history.user_id = :id
                AND history.purged = false
        ),
        per_hist_hdas AS (
            SELECT DISTINCT history_dataset_association.dataset_id as id
            FROM history_dataset_association
            WHERE history_dataset_association.purged = false
                AND history_dataset_association.history_id in (SELECT id from per_user_histories)
        )
    """

    sql_calc = """
        SELECT sum(coalesce(dataset.total_size, coalesce(dataset.file_size, 0)))
        FROM dataset
        LEFT OUTER JOIN library_dataset_dataset_association ON dataset.id = library_dataset_dataset_association.dataset_id
        WHERE dataset.id in (SELECT id from per_hist_hdas)
            AND library_dataset_dataset_association.id IS NULL
    """

    sql_update = """UPDATE galaxy_user
                    SET disk_usage = (%s)
                    WHERE id = :id
                    RETURNING disk_usage;""" % sql_calc
    if dryrun:
        r = sa_session.execute(ctes + sql_calc, {'id': id})
    else:
        r = sa_session.execute(ctes + sql_update, {'id': id})
    return r.fetchone()[0]
