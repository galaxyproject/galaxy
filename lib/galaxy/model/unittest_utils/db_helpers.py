from sqlalchemy import select

from galaxy import model


def get_hdca_by_name(session, name):
    stmt = (
        select(model.HistoryDatasetCollectionAssociation)
        .where(model.HistoryDatasetCollectionAssociation.name == name)
        .limit(1)
    )
    return session.scalars(stmt).first()
