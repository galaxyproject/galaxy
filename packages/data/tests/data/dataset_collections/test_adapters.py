from galaxy import model
from galaxy.model.dataset_collections.adapters import (
    PromoteDatasetsToCollection,
    TransientCollectionAdapterDatasetInstanceElement,
)


def _hda_with_actions(actions):
    dataset = model.Dataset()
    for action, role_id in actions:
        model.DatasetPermissions(action, dataset, role_id=role_id)
    return model.HistoryDatasetAssociation(dataset=dataset)


def test_promote_datasets_to_collection_dataset_action_tuples_are_flat():
    forward = _hda_with_actions([("access", 1)])
    reverse = _hda_with_actions([("access", 2), ("manage permissions", 3), ("manage permissions", 4)])
    adapter = PromoteDatasetsToCollection(
        [
            TransientCollectionAdapterDatasetInstanceElement("forward", forward),
            TransientCollectionAdapterDatasetInstanceElement("reverse", reverse),
        ],
        "paired",
    )
    assert adapter.dataset_action_tuples == [
        ("access", 1),
        ("access", 2),
        ("manage permissions", 3),
        ("manage permissions", 4),
    ]
