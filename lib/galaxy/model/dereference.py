import os.path

from galaxy.model import (
    DatasetSource,
    HistoryDatasetAssociation,
)
from galaxy.tool_util.parameters import DataRequestUri


def dereference_to_model(sa_session, user, history, data_request_uri: DataRequestUri) -> HistoryDatasetAssociation:
    # based on code from upload_common
    name = os.path.basename(data_request_uri.url)
    dbkey = "?"
    hda = HistoryDatasetAssociation(
        name=name,
        extension=data_request_uri.ext,
        dbkey=dbkey,  # TODO
        history=history,
        create_dataset=True,
        sa_session=sa_session,
    )
    hda.state = hda.states.DEFERRED
    dataset_source = DatasetSource()
    dataset_source.source_uri = data_request_uri.url
    hda.dataset.sources = [dataset_source]

    sa_session.add(hda)
    sa_session.add(dataset_source)
    history.add_dataset(hda, genome_build=dbkey, quota=False)
    return hda
