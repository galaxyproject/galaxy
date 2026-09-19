import json
import logging
import os
import re

from galaxy.util import stringify_dictionary_keys

log = logging.getLogger(__name__)


def parse_tool_provided_metadata(meta_file, provided_metadata_style=None, job_wrapper=None):
    """Return a ToolProvidedMetadata object for specified file path.

    If meta_file is absent, return a NullToolProvidedMetadata. If provided_metadata_style is None
    attempt to guess tool provided metadata type.
    """
    if not os.path.exists(meta_file):
        return NullToolProvidedMetadata()
    if provided_metadata_style is None:
        provided_metadata_style = _guess_tool_provided_metadata_style(meta_file)

    assert provided_metadata_style in ["legacy", "default"]

    if provided_metadata_style == "legacy":
        return LegacyToolProvidedMetadata(meta_file, job_wrapper=job_wrapper)
    elif provided_metadata_style == "default":
        return ToolProvidedMetadata(meta_file)


def _guess_tool_provided_metadata_style(path):
    try:
        with open(path) as f:
            metadata = json.load(f)
        metadata_type = metadata.get("type", None)
        return "legacy" if metadata_type in ["dataset", "new_primary_dataset"] else "default"
    except ValueError:
        # Either empty or multiple JSON lines, either way we can safely treat
        # it as legacy style.
        return "legacy"


class BaseToolProvidedMetadata:
    def get_new_datasets(self, output_name):
        """Find new datasets for dataset discovery for specified output.

        Return a list of such datasets.

        Called only in the context of discovering datasets when
        discover_via="tool_provided_metadata" is defined in the tool.
        """
        return []

    def has_failed_outputs(self):
        """Determine if generation of any of the outputs failed.

        If True, this method should also log information about at least the first such failed output.
        """
        return False

    def get_new_dataset_meta_by_basename(self, output_name, basename):
        """For a discovered dataset, get the corresponding metadata entry.

        The discovery may have been from explicit listing in this file (returned
        from get_new_datasets) or via file regex, either way the basename of the
        file is used to index the fetching of the metadata entry.
        """
        return {}

    def get_unnamed_outputs(self):
        """Return unnamed outputs dataset introduced for upload 2.0.

        Needs more formal specification but see output_collect for how destinations,
        types, elements, etc... are consumed.
        """
        return []

    def get_dataset_meta(self, output_name, dataset_id, dataset_uuid):
        """Return primary dataset metadata for specified output."""
        return {}

    def rewrite(self):
        """Write metadata back to the file system.

        If metadata has not changed via outputs specified as mutable, the
        implementation class may opt to not re-write the file.
        """
        return None

    def get_new_datasets_for_metadata_collection(self):
        """Return all datasets tracked that are not explicit primary outputs."""
        return []


class NullToolProvidedMetadata(BaseToolProvidedMetadata):
    pass


class LegacyToolProvidedMetadata(BaseToolProvidedMetadata):
    def __init__(self, meta_file, job_wrapper=None):
        self.meta_file = meta_file
        self.tool_provided_job_metadata = []

        with open(meta_file) as f:
            for line in f:
                try:
                    line_as_dict = stringify_dictionary_keys(json.loads(line))
                    assert "type" in line_as_dict
                except Exception as e:
                    message = f'Got JSON data from tool, but line is improperly formatted or no "type" key in: [{line}]'
                    raise ValueError(message) from e
                # Set the dataset id if it's a dataset entry and isn't set.
                # This isn't insecure.  We loop the job's output datasets in
                # the finish method, so if a tool writes out metadata for a
                # dataset id that it doesn't own, it'll just be ignored.
                dataset_id_not_specified = line_as_dict["type"] == "dataset" and "dataset_id" not in line_as_dict
                if dataset_id_not_specified:
                    dataset_basename = line_as_dict["dataset"]
                    if job_wrapper:
                        try:
                            line_as_dict["dataset_id"] = job_wrapper.job_io.get_output_file_id(dataset_basename)
                        except KeyError:
                            log.warning(
                                f"({job_wrapper.job_id}) Tool provided job dataset-specific metadata without specifying a dataset"
                            )
                            continue
                    else:
                        match = re.match(r"(galaxy_)?dataset_(.*)\.dat", dataset_basename)
                        if match is None:
                            raise Exception(
                                f"processing tool_provided_metadata (e.g. galaxy.json) entry with invalid dataset name [{dataset_basename}]"
                            )
                        dataset_id = match.group(2)
                        if dataset_id.isdigit():
                            line_as_dict["dataset_id"] = dataset_id
                        else:
                            line_as_dict["dataset_uuid"] = dataset_id

                self.tool_provided_job_metadata.append(line_as_dict)

    def get_dataset_meta(self, output_name, dataset_id, dataset_uuid):
        for meta in self.tool_provided_job_metadata:
            if meta["type"] == "dataset" and "dataset_id" in meta and int(meta["dataset_id"]) == dataset_id:
                return meta
            if meta["type"] == "dataset" and "dataset_uuid" in meta and meta["dataset_uuid"] == dataset_uuid:
                return meta
        return {}

    def get_new_dataset_meta_by_basename(self, output_name, basename):
        for meta in self.tool_provided_job_metadata:
            if meta["type"] == "new_primary_dataset" and meta["filename"] == basename:
                return meta

    def get_new_datasets(self, output_name):
        log.warning("Called get_new_datasets with legacy tool metadata provider - that is unimplemented.")
        return []

    def has_failed_outputs(self):
        found_failed = False
        for meta in self.tool_provided_job_metadata:
            if meta.get("failed", False):
                log.info(f"One or more tool outputs is marked as failed ({meta}).")
                found_failed = True

        return found_failed

    def get_unnamed_outputs(self):
        return []

    def rewrite(self):
        with open(self.meta_file, "w") as job_metadata_fh:
            for meta in self.tool_provided_job_metadata:
                job_metadata_fh.write(f"{json.dumps(meta)}\n")

    def get_new_datasets_for_metadata_collection(self):
        for meta in self.tool_provided_job_metadata:
            if meta["type"] == "new_primary_dataset":
                yield meta


class ToolProvidedMetadata(BaseToolProvidedMetadata):
    def __init__(self, meta_file):
        self.meta_file = meta_file
        with open(meta_file) as f:
            self.tool_provided_job_metadata = json.load(f)

    def get_dataset_meta(self, output_name, dataset_id, dataset_uuid):
        return self.tool_provided_job_metadata.get(output_name, {})

    def get_new_dataset_meta_by_basename(self, output_name, basename):
        datasets = self.tool_provided_job_metadata.get(output_name, {}).get("datasets", [])
        for meta in datasets:
            if meta["filename"] == basename:
                return meta

    def get_new_datasets(self, output_name):
        datasets = self.tool_provided_job_metadata.get(output_name, {}).get("datasets", [])
        if not datasets:
            elements = self.tool_provided_job_metadata.get(output_name, {}).get("elements", [])
            if elements:
                datasets = self._elements_to_datasets(elements)
        return datasets

    def _elements_to_datasets(self, elements, level=0):
        for element in elements:
            extra_kwds = {f"identifier_{level}": element["name"]}
            if "elements" in element:
                for inner_element in self._elements_to_datasets(element["elements"], level=level + 1):
                    dataset = extra_kwds.copy()
                    dataset.update(inner_element)
                    yield dataset
            else:
                dataset = extra_kwds
                extra_kwds.update(element)
                yield extra_kwds

    def has_failed_outputs(self):
        found_failed = False
        for output_name, meta in self.tool_provided_job_metadata.items():
            if output_name == "__unnamed_outputs":
                continue

            if meta.get("failed", False):
                log.info(f"One or more tool outputs is marked as failed ({meta}).")
                found_failed = True

        return found_failed

    def get_unnamed_outputs(self):
        log.debug(f"unnamed outputs [{self.tool_provided_job_metadata}]")
        return self.tool_provided_job_metadata.get("__unnamed_outputs", [])

    def rewrite(self):
        with open(self.meta_file, "w") as job_metadata_fh:
            json.dump(self.tool_provided_job_metadata, job_metadata_fh)
