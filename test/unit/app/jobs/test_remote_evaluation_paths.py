from typing import (
    Any,
    cast,
)

from galaxy.job_execution.compute_environment import (
    remote_evaluation_paths,
    RemoteComputeEnvironment,
)
from galaxy.model import (
    Dataset,
    MetadataFile,
)


class _Dataset:
    def __init__(self, id):
        self.id = id
        self.uuid = None

    def extra_files_path_exists(self):
        return False


def _metadata_file(path):
    metadata_file = MetadataFile()
    metadata_file.uuid = None
    metadata_file.get_file_name = lambda sync_cache=True, auth=None: path  # type: ignore[method-assign]
    return metadata_file


class _HistoryDatasetAssociation:
    state = Dataset.states.OK

    def __init__(self, id, dataset, metadata):
        self.id = id
        self.dataset = dataset
        self.metadata = metadata


class _JobIO:
    def __init__(self, inputs, outputs):
        self.inputs = inputs
        self.outputs = outputs

    def get_input_datasets(self):
        return self.inputs

    def get_input_path(self, dataset):
        return f"/galaxy/objects/dataset_{dataset.dataset.id}.dat"

    def get_output_hdas_and_fnames(self):
        return {
            f"output{i}": (dataset, f"/galaxy/objects/dataset_{dataset.dataset.id}.dat")
            for i, dataset in enumerate(self.outputs)
        }


class _ComputeEnvironment:
    def input_path_rewrite(self, dataset):
        return f"/compute/inputs/dataset_{dataset.dataset.id}.dat"

    def output_path_rewrite(self, dataset):
        return f"/compute/outputs/dataset_{dataset.dataset.id}.dat"

    def input_metadata_rewrite(self, dataset, metadata_name, metadata_file):
        return None


def test_files_without_uuids_resolve_to_their_own_paths():
    bam_1 = _HistoryDatasetAssociation(1, _Dataset(11), {"bam_index": _metadata_file("/galaxy/metadata_1.dat")})
    bam_2 = _HistoryDatasetAssociation(2, _Dataset(12), {"bam_index": _metadata_file("/galaxy/metadata_2.dat")})
    output = _HistoryDatasetAssociation(3, _Dataset(13), {})
    job_io = _JobIO([bam_1, bam_2], [output])

    paths = remote_evaluation_paths(cast(Any, job_io), cast(Any, _ComputeEnvironment()))
    compute_environment = RemoteComputeEnvironment(cast(Any, job_io), cast(Any, None), paths)

    assert compute_environment.input_path_rewrite(bam_1) == "/compute/inputs/dataset_11.dat"
    assert compute_environment.input_path_rewrite(bam_2) == "/compute/inputs/dataset_12.dat"
    assert compute_environment.output_path_rewrite(output) == "/compute/outputs/dataset_13.dat"
    assert (
        compute_environment.input_metadata_rewrite(bam_1, "bam_index", bam_1.metadata["bam_index"])
        == "/galaxy/metadata_1.dat"
    )
    assert (
        compute_environment.input_metadata_rewrite(bam_2, "bam_index", bam_2.metadata["bam_index"])
        == "/galaxy/metadata_2.dat"
    )
