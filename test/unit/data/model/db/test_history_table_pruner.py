import datetime

import pytest
from sqlalchemy import (
    func,
    select,
)

from galaxy import model as m
from galaxy.model.scripts.history_table_pruner import HistoryTablePruner


@pytest.fixture()
def setup_db(
    db_url,
    session,
    make_user,
    make_history,
    make_event,
    make_history_tag_association,
    make_history_annotation_association,
    make_history_rating_association,
    make_history_user_share_association,
    make_default_history_permissions,
    make_data_manager_history_association,
    make_cleanup_event_history_association,
    make_galaxy_session_to_history_association,
    make_job_import_history_archive,
    make_job_export_history_archive,
    make_workflow_invocation,
    make_history_dataset_collection_association,
    make_job,
    make_history_dataset_association,
    make_galaxy_session,
):
    # 1. Create 100 histories; make them deletable: user = null, hid_counter = 1.
    histories = []
    for id in range(100):
        h = make_history(id=id)
        h.user = None
        h.hid_counter = 1
        histories.append(h)

    # 2. Set 10 histories as not deletable: hid_counter != 1.
    for i in range(10):
        histories[i].hid_counter = 42

    # 3. Set next 10 histories as not deletable: user not null.
    u = make_user()
    for i in range(10, 20):
        histories[i].user = u

    # 4. For the next 6 histories create associations that cannot be deleted.
    make_job_import_history_archive(history=histories[20])
    make_job_export_history_archive(history=histories[21])
    make_workflow_invocation(history=histories[22])
    make_history_dataset_collection_association(history=histories[23])
    make_history_dataset_association(history=histories[25])
    make_job().history = histories[24]

    # 5. For the next 10 histories create associations that can be deleted.
    make_event(history=histories[26])
    make_history_tag_association(history=histories[27])
    make_history_annotation_association(history=histories[28])
    make_history_rating_association(item=histories[29])
    make_history_user_share_association(history=histories[30])
    make_default_history_permissions(history=histories[31])
    make_data_manager_history_association(history=histories[32])
    make_cleanup_event_history_association(history_id=histories[33].id)
    make_galaxy_session_to_history_association(history=histories[34])

    # 6. Create a galaxy_session record referring to a history.
    # This cannot be deleted, but the history reference can be set to null.
    make_galaxy_session(current_history=histories[36])

    session.commit()

    # TOTAL counts of loaded histories:
    # histories that should NOT be deleted: 10 + 10 + 6 = 26
    # histories that SHOULD be deleted: 100 - 26 = 74


def test_run(setup_db, session, db_url, engine):
    # In this test we do not verify counts of rows in the HistoryAudit table since those rows are created
    # automatically via db trigger.
    def verify_counts(model, expected):
        assert session.scalar(select(func.count()).select_from(model)) == expected

    # 1. Verify history counts
    stmt = select(m.History).order_by(m.History.id)
    result = session.scalars(stmt).all()
    assert len(result) == 100
    for i, h in enumerate(result):
        if i < 10:  # first 10
            assert h.hid_counter > 1
            assert h.user is None
        elif i < 20:  # next 10
            assert h.hid_counter == 1
            assert h.user is not None
        else:  # the rest
            assert h.hid_counter == 1
            assert h.user is None

    # 2. Verify association counts
    for model in [
        m.JobImportHistoryArchive,
        m.JobExportHistoryArchive,
        m.WorkflowInvocation,
        m.HistoryDatasetCollectionAssociation,
        m.Job,
        m.HistoryDatasetAssociation,
        m.Event,
        m.HistoryTagAssociation,
        m.HistoryAnnotationAssociation,
        m.HistoryRatingAssociation,
        m.HistoryUserShareAssociation,
        m.DefaultHistoryPermissions,
        m.DataManagerHistoryAssociation,
        m.CleanupEventHistoryAssociation,
        m.GalaxySessionToHistoryAssociation,
    ]:
        verify_counts(model, 1)
    verify_counts(
        m.GalaxySession, 2
    )  # one extra session was automatically created for GalaxySessionToHistoryAssociation

    # 3. Run pruning script
    today = datetime.date.today()
    newdate = today.replace(year=today.year + 1)
    HistoryTablePruner(engine, max_create_time=newdate).run()

    # 4 Verify new counts (for details on expected counts see comments in setup_db)

    # 4.1 Verify new history counts
    verify_counts(m.History, 26)

    # 4.2 Verify new association counts: no change (these associations should NOT be deleted)
    for model in [
        m.JobImportHistoryArchive,
        m.JobExportHistoryArchive,
        m.WorkflowInvocation,
        m.HistoryDatasetCollectionAssociation,
        m.Job,
        m.HistoryDatasetAssociation,
    ]:
        verify_counts(model, 1)
    verify_counts(m.GalaxySession, 2)

    # 4.3 Verify new association counts: deleted (these associations SHOULD be deleted)
    for model in [
        m.Event,
        m.HistoryTagAssociation,
        m.HistoryAnnotationAssociation,
        m.HistoryRatingAssociation,
        m.HistoryUserShareAssociation,
        m.DefaultHistoryPermissions,
        m.DataManagerHistoryAssociation,
        m.CleanupEventHistoryAssociation,
        m.GalaxySessionToHistoryAssociation,
    ]:
        verify_counts(model, 0)
