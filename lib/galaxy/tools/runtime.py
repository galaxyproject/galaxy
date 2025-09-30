from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy.model import (
    HistoryDatasetAssociation,
    InpDataDictT,
)
from galaxy.tool_util.cwl.util import set_basename_and_derived_properties
from galaxy.tool_util_models.parameters import (
    DataInternalJson,
    DataRequestInternalDereferencedT,
)

if TYPE_CHECKING:
    from galaxy.job_execution.compute_environment import ComputeEnvironment
    from galaxy.structured_app import MinimalToolApp


def setup_for_runtimeify(
    app: "MinimalToolApp", compute_environment: Optional["ComputeEnvironment"], input_datasets: InpDataDictT
):
    hda_references: list[HistoryDatasetAssociation] = []

    hdas_by_id = {d.id: (d, i) for (i, d) in enumerate(input_datasets.values()) if d is not None}

    def adapt_dataset(value: DataRequestInternalDereferencedT) -> DataInternalJson:
        hda_id = value.id
        if hda_id not in hdas_by_id:
            raise ValueError(f"Could not find HDA for dataset id {hda_id}")
        hda, index = hdas_by_id[hda_id]
        if not hda:
            raise ValueError(f"Could not find HDA for dataset id {hda_id}")
        size = hda.dataset.get_size() if hda and hda.dataset else 0
        properties = {
            "class": "File",
            "location": f"step_input://{index}",
            "format": hda.extension,
            "path": compute_environment.input_path_rewrite(hda) if compute_environment else hda.get_file_name(),
            "size": int(size),
            "listing": [],
        }
        set_basename_and_derived_properties(properties, hda.dataset.created_from_basename or hda.name)
        return DataInternalJson(**properties)

    def adapt_collection(value):
        pass

    return hda_references, adapt_dataset
