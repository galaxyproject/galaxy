"""
Utility helpers related to the model
"""


def count_toward_deleted_disk_usage(dataset_id, history_deleted, hda_deleted, dataset_deleted, dataset_disk_usage, ids_dict):
    """
    ids_dict: stores the state of dataset and its associated hda and history, key=str(dataset_id), value could be one of following.
        -1: dataset deleted
        0: dataset not deleted, history deleted, hda deleted
        1: dataset not deleted, history deleted, hda not deleted
        2: dataset not deleted, history not deleted, hda deleted
        3: dataset not deleted, history not deleted, hda not deleted

    Return:
    disk usage counted toward deleted disk usage for the input dataset
    """
    id_key = str(dataset_id)

    # already counted, state is fixed
    if id_key in ids_dict and (ids_dict[id_key] == -1 or ids_dict[id_key] == 3):
        return 0

    # first occurence
    # count all datasets that keep possibilty to be counted in the end
    # add dataset_id and state to ids_dict
    if id_key not in ids_dict:
        if dataset_deleted:
            ids_dict[id_key] = -1    # count
            return dataset_disk_usage
        elif hda_deleted:
            if history_deleted:      # possible to be counted, count temporally
                ids_dict[id_key] = 0
                return dataset_disk_usage
            else:                    # possible to be counted, count temporally
                ids_dict[id_key] = 2
                return dataset_disk_usage
        else:
            if history_deleted:     # possible to be counted, count temporally
                ids_dict[id_key] = 1
                return dataset_disk_usage
            else:                   # not possible to be counted, do not count
                ids_dict[id_key] = 3
                return 0

    # repeating occurrence, update state as needed
    else:
        if hda_deleted:
            if history_deleted:
                ids_dict[id_key] = ids_dict[id_key] | 0
            else:
                ids_dict[id_key] = ids_dict[id_key] | 2
        else:
            if history_deleted:
                ids_dict[id_key] = ids_dict[id_key] | 1
            else:
                ids_dict[id_key] = 3

        if ids_dict[id_key] == 3:   # previously-counted dataset turns out to be not countable
            return -dataset_disk_usage
        else:
            return 0


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
            deleted_count = count_toward_deleted_disk_usage(
                dataset_id,
                history_deleted,
                hda_deleted,
                dataset_deleted,
                dataset_total_size,
                ids_dict)
            deleted += deleted_count
    if not dryrun:
        sql_update = """UPDATE galaxy_user
                    SET disk_usage = (%s), deleted_disk_usage = (%s)
                    WHERE id = :id;""" % (total, deleted)
        sa_session.execute(sql_update, {'id': id})
    return (total, deleted)



def disk_usage(db_session, History, user_id, HistoryDatasetAssociation, Dataset):
    ids_dict = {}
    total = 0
    deleted = 0

    # this can be a huge number and can run out of memory, so we avoid the mappers
    for history in db_session.query(History).enable_eagerloads(False).filter_by(user_id=user_id, purged=False).yield_per(1000):
        for hda, dataset in db_session.query(
            HistoryDatasetAssociation, Dataset).enable_eagerloads(False).join(Dataset).filter(and_(
                HistoryDatasetAssociation.history_id == history.id,
                HistoryDatasetAssociation.purged != true(),
                Dataset.purged != true())).yield_per(1000):
            # TODO: def hda.counts_toward_disk_usage():
            #   return ( not self.dataset.purged and not self.dataset.library_associations )
            if dataset.library_associations:
                continue
            if str(dataset.id) not in ids_dict:
                total += dataset.get_total_size()
            deleted_count = count_toward_deleted_disk_usage(
                dataset.id,
                history.deleted,
                hda.deleted,
                dataset.deleted,
                dataset.get_total_size(),
                ids_dict)
            deleted += deleted_count
    return (total, deleted)



def calculate_and_set_disk_usage(db_session, user):
    total = None
    deleted = None

    current_total = user.get_disk_usage()
    current_deleted = user.get_deleted_disk_usage()
    if db_session.get_bind().dialect.name not in ('postgres', 'postgresql'):
        done = False
        while not done:
            total, deleted = user.calculate_disk_usage()
            db_session.refresh(user)
            # make sure usage didn't change while calculating
            # set done if it has not, otherwise reset current and iterate again.
            if user.get_disk_usage() == current_total and user.get_deleted_disk_usage() == current_deleted:
                done = True
            else:
                current_total = user.get_disk_usage()
                current_deleted = user.get_deleted_disk_usage()
    else:
        total, deleted = pgcalc(db_session, user.id)
    if total not in (current_total, None) or deleted not in (current_deleted, None):
        user.set_disk_usage(total)
        user.set_deleted_disk_usage(deleted)
        db_session.add(user)
        db_session.flush()

