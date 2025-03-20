import os.path
from typing import List

from galaxy.model import (
    DatasetSource,
    DatasetSourceHash,
    HistoryDatasetAssociation,
    TransformAction,
)
from galaxy.tool_util.parameters import DataRequestUri


def dereference_to_model(sa_session, user, history, data_request_uri: DataRequestUri) -> HistoryDatasetAssociation:
    name = data_request_uri.name or os.path.basename(data_request_uri.url)
    dbkey = data_request_uri.dbkey or "?"
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
    hashes = []
    for dataset_hash in data_request_uri.hashes or []:
        hash_object = DatasetSourceHash()
        hash_object.hash_function = dataset_hash.hash_function
        hash_object.hash_value = dataset_hash.hash_value
        hashes.append(hash_object)
    dataset_source.hashes = hashes
    hda.dataset.sources = [dataset_source]
    transform: List[TransformAction] = []
    if data_request_uri.space_to_tab:
        transform.append({"action": "spaces_to_tabs"})
    elif data_request_uri.to_posix_lines:
        transform.append({"action": "to_posix_lines"})
    if len(transform) > 0:
        dataset_source.transform = transform

    sa_session.add(hda)
    sa_session.add(dataset_source)
    history.add_dataset(hda, genome_build=dbkey, quota=False)
    return hda
