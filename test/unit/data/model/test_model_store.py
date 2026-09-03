"""Unit tests for importing and exporting data from model stores."""

import json
import os
import pathlib
import shutil
import sys
from tempfile import (
    mkdtemp,
    NamedTemporaryFile,
)
from types import SimpleNamespace
from typing import (
    Any,
    NamedTuple,
)
from unittest.mock import Mock

import pytest
from rocrate.rocrate import ROCrate
from rocrate_validator import (
    models,
    services,
)
from sqlalchemy import select

from galaxy import model
from galaxy.model import store
from galaxy.model.metadata import MetadataTempFile
from galaxy.model.scoped_session import galaxy_scoped_session as scoped_session
from galaxy.model.store import SessionlessContext
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    one_hda_model_store_dict,
    one_ld_library_model_store_dict,
    TEST_HASH_FUNCTION,
    TEST_HASH_VALUE,
    TEST_SOURCE_URI,
)
from galaxy.objectstore.unittest_utils import Config as TestConfig
from galaxy.tools.source_store import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.util.compression_utils import CompressedFile
from ..test_galaxy_mapping import (
    _invocation_for_workflow,
    _workflow_from_steps,
)

TESTCASE_DIRECTORY = pathlib.Path(__file__).parent
TEST_PATH_1 = TESTCASE_DIRECTORY / "1.txt"
TEST_PATH_2 = TESTCASE_DIRECTORY / "2.bed"
TEST_PATH_2_CONVERTED = TESTCASE_DIRECTORY / "2.txt"
DEFAULT_OBJECT_STORE_BY = "id"


def test_ro_crate_tool_definition_metadata():
    writer = store.WriteCrates()
    definition = SimpleNamespace(
        version="1.2",
        name="Example analysis",
        description="Tool description",
        license="MIT",
        edam_operations=["operation_0004"],
        edam_topics=["topic_0091"],
        citations=[
            SimpleNamespace(has_doi=lambda: True, doi=lambda: "doi:10.1234/example"),
            SimpleNamespace(has_doi=lambda: False, raw_bibtex="@article{example,title={Example}}"),
        ],
        xrefs=[{"type": "bio.tools", "value": "example"}],
        creator=[{"class": "Person", "name": "Author", "email": "private@example.com"}],
        requirements=[SimpleNamespace(name="python", version="3.12")],
        containers=[SimpleNamespace(identifier="example:1.2", type="docker")],
        tool_shed="toolshed.example.org",
        repository_name="example",
        repository_owner="owner",
        changeset_revision="abc123",
    )
    cached_tool = SimpleNamespace(version="1.2")
    writer.app = SimpleNamespace(
        toolbox=SimpleNamespace(get_tool=Mock(return_value=cached_tool), materialize_tool=Mock(return_value=definition))
    )
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": writer._tool_entity_id("example", "1.2"), "@type": "SoftwareApplication"})
    writer._enrich_tool_entity(crate, entity, "example", "1.2")
    writer.app.toolbox.get_tool.assert_called_once_with("example", tool_version="1.2", exact=True)
    writer.app.toolbox.materialize_tool.assert_called_once_with(cached_tool, reason="serialization")
    assert entity["name"] == "Example analysis"
    assert entity["softwareVersion"] == "1.2"
    assert entity.get("version") is None
    assert entity["license"] == "MIT"
    assert entity["featureList"][0].id == "http://edamontology.org/operation_0004"
    assert entity["about"][0].id == "http://edamontology.org/topic_0091"
    assert entity["citation"][0].id == "https://doi.org/10.1234/example"
    assert entity["citation"][1]["encodingFormat"] == "application/x-bibtex"
    assert entity["creator"][0].get("email") is None
    assert entity["softwareRequirements"][0]["softwareVersion"] == "3.12"
    values = {item["name"]: item["value"] for item in entity["additionalProperty"]}
    assert values["ToolShed changeset_revision"] == "abc123"
    assert json.loads(values["Declared container 1"])["type"] == "docker"


def test_ro_crate_missing_exact_tool_version():
    writer = store.WriteCrates()
    writer.app = SimpleNamespace(toolbox=SimpleNamespace(get_tool=Mock(return_value=SimpleNamespace(version="2"))))
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication", "name": "recorded"})
    writer._enrich_tool_entity(crate, entity, "example", "1")
    assert entity["name"] == "recorded"
    assert entity["softwareVersion"] == "1"
    assert entity.get("citation") is None
    assert writer._tool_entity_id("a/b", "1") != writer._tool_entity_id("a-b", "1")


def test_ro_crate_tool_metadata_without_toolbox():
    class ToolboxlessApp:
        @property
        def toolbox(self):
            raise AssertionError("The toolbox property must not be accessed")

        @property
        def toolbox_or_none(self):
            return None

    writer = store.WriteCrates()
    writer.app = ToolboxlessApp()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication", "name": "Recorded tool"})

    writer._enrich_tool_entity(crate, entity, "example", "1.0")

    assert entity["identifier"] == "example"
    assert entity["softwareVersion"] == "1.0"
    availability = next(item for item in entity["additionalProperty"] if item["name"] == "Tool metadata availability")
    assert availability["value"] == "Exact recorded tool version unavailable"


@pytest.mark.parametrize(
    "value",
    [
        '["/private/data"]',
        '"C:\\\\private\\\\data"',
        "https://example.org/data?token=secret",
        "https://user:password@example.org/data",
        "file:///private/data",
    ],
)
def test_ro_crate_private_locations_are_rejected(value):
    try:
        value = json.loads(value)
    except ValueError:
        pass
    assert not store.WriteCrates._safe_metadata_value(value)


def test_ro_crate_parameter_type_mapping():
    from galaxy.model.store.ro_crate_utils import (
        ro_crate_parameter_type,
        RO_CRATE_PARAMETER_TYPES,
    )
    from galaxy.tools.parameters.basic import parameter_types

    assert ro_crate_parameter_type("data_column") == "Integer"
    assert ro_crate_parameter_type("hidden_data") == "File"
    assert ro_crate_parameter_type("baseurl") == "URL"
    assert ro_crate_parameter_type("rules") == "PropertyValue"
    assert ro_crate_parameter_type("future_parameter") == "Thing"
    assert set(parameter_types).issubset(RO_CRATE_PARAMETER_TYPES)


def test_model_store_metadata_file_registry_is_complete():
    from galaxy.model.store import model_store_constants

    defined = {
        value
        for name, value in vars(model_store_constants).items()
        if name.startswith("ATTRS_FILENAME_") and isinstance(value, str)
    }
    assert defined.issubset(model_store_constants.MODEL_STORE_METADATA_FILENAMES)


def test_ro_crate_tool_source_index_enrichment():
    class ToolboxlessApp:
        toolbox_or_none = None
        tool_source_store = SimpleNamespace(
            load_index=lambda: ToolIndex(
                entries_by_version={
                    "example": {
                        "1.0": ToolIndexEntry(
                            id="example",
                            version="1.0",
                            name="Example Tool",
                            license="MIT",
                            edam_operations=["operation_0004"],
                            citations=[{"type": "doi", "content": "10.1234/example"}],
                        )
                    }
                }
            )
        )

    writer = store.WriteCrates()
    writer.app = ToolboxlessApp()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication"})
    writer._enrich_tool_entity(crate, entity, "example", "1.0")
    assert entity["name"] == "Example Tool"
    assert entity["license"] == "MIT"
    assert entity["featureList"][0].id == "http://edamontology.org/operation_0004"
    assert entity["citation"][0].id == "https://doi.org/10.1234/example"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), {"n": float("nan")}])
def test_ro_crate_nonfinite_metadata_is_rejected(value):
    assert not store.WriteCrates._safe_metadata_value(value)


def test_ro_crate_property_identity_and_deduplication():
    writer = store.WriteCrates()
    crate = ROCrate()
    entity = crate.root_dataset
    writer._add_metadata_property(crate, entity, "Requirement", "one")
    writer._add_metadata_property(crate, entity, "Requirement", "two")
    writer._add_metadata_property(crate, entity, "Requirement", "one")
    assert [p["value"] for p in entity["additionalProperty"]] == ["one", "two"]
    assert len({p.id for p in entity["additionalProperty"]}) == 2


def test_ro_crate_step_defaults_do_not_mutate_shared_tool():
    from galaxy.model.store.ro_crate_utils import WorkflowRunCrateProfileBuilder

    crate = ROCrate()
    tool = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication"})
    workflow = crate.add_jsonld({"@id": "#workflow", "@type": "ComputationalWorkflow"})
    builder = object.__new__(WorkflowRunCrateProfileBuilder)
    builder.model_store = store.WriteCrates()
    builder.workflow_definitions = {1: workflow}
    builder.step_cache = {}
    steps = []
    for index, default in ((1, 10), (2, 20)):
        steps.append(
            SimpleNamespace(
                id=index,
                workflow_id=1,
                type="tool",
                label="step",
                inputs=[
                    SimpleNamespace(name="threshold", default_value_set=True, default_value=default, connections=[]),
                ],
            )
        )
        builder.step_cache[index] = crate.add_jsonld(
            {"@id": f"#step-{index}", "@type": "HowToStep", "workExample": {"@id": tool.id}}
        )
    builder.model_store.included_invocations = [
        SimpleNamespace(
            workflow_id=1,
            workflow=SimpleNamespace(id=1, steps=steps),
            output_datasets=[],
            output_dataset_collections=[],
            output_values=[],
        )
    ]
    builder._add_connections(crate)
    assert tool["input"][0].get("defaultValue") is None
    assert [builder.step_cache[index]["additionalProperty"][0]["value"] for index in (1, 2)] == [10, 20]


def test_ro_crate_recorded_hash_is_not_export_hash():
    writer = store.WriteCrates()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#dataset", "@type": "Dataset"})
    writer._attach_dataset_checksum(crate, entity, {"_galaxy_sha256": "a" * 64})
    writer._attach_dataset_metadata(
        crate,
        entity,
        SimpleNamespace(
            metadata=SimpleNamespace(),
            dataset=SimpleNamespace(
                sources=[],
                hashes=[SimpleNamespace(hash_function="SHA-256", hash_value="b" * 64, extra_files_path=None)],
            ),
        ),
    )
    checksums = entity["additionalProperty"]
    assert checksums[0]["value"] == "a" * 64
    assert checksums[1]["value"] == "b" * 64
    assert "not verified against exported bytes" in checksums[1]["name"]


def test_ro_crate_dynamic_tool_and_static_constraints():
    writer = store.WriteCrates()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication"})
    writer._add_dynamic_tool_metadata(
        crate,
        entity,
        SimpleNamespace(
            uuid="11111111-1111-1111-1111-111111111111",
            tool_id="dynamic",
            tool_format="GalaxyTool",
            tool_version="1",
            create_time=None,
            update_time=None,
            value={"description": "Recorded tool", "command": "private command"},
        ),
    )
    assert entity["isBasedOn"][0]["identifier"].startswith("urn:uuid:")
    assert "private command" not in json.dumps([e.as_jsonld() for e in crate.get_entities()])
    writer._add_tool_ports(
        crate,
        entity,
        SimpleNamespace(
            inputs={
                "threshold": SimpleNamespace(
                    type="integer",
                    optional=False,
                    value=0,
                    min=0,
                    max=10,
                    is_dynamic=False,
                )
            }
        ),
    )
    assert entity["input"][0]["defaultValue"] == 0
    assert entity["input"][0]["valueRequired"] is True


def test_ro_crate_conditional_branch_values():
    writer = store.WriteCrates()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication"})
    selector = SimpleNamespace(name="mode", type="select")
    cases = [
        SimpleNamespace(value="keep", inputs={"limit": SimpleNamespace(type="integer")}),
        SimpleNamespace(value="drop", inputs={"limit": SimpleNamespace(type="integer")}),
    ]
    writer._add_tool_ports(
        crate,
        entity,
        SimpleNamespace(inputs={"choice": SimpleNamespace(type="conditional", test_param=selector, cases=cases)}),
    )
    branches = [
        json.loads(prop["value"])
        for prop in entity["input"][0]["additionalProperty"]
        if prop["name"] == "Galaxy conditional branch"
    ]
    assert [branch["value"] for branch in branches] == ["keep", "drop"]


def test_ro_crate_tool_port_private_default_is_withheld():
    writer = store.WriteCrates()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication"})
    writer._add_tool_ports(
        crate,
        entity,
        SimpleNamespace(inputs={"api_token": SimpleNamespace(type="text", value="marker", is_dynamic=False)}),
    )
    assert entity["input"][0].get("defaultValue") is None


def test_ro_crate_job_input_adapters(tmp_path):
    app = _mock_app()
    _, _, dataset, output, job = _setup_simple_cat_job(app)
    job.input_datasets[0].adapter = {
        "src": "CollectionAdapter",
        "adapter_type": "PromoteDatasetToCollection",
        "collection_type": "list",
        "adapting": {"src": "hda", "id": dataset.id},
    }
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(output)
    crate = ROCrate(tmp_path)
    adapter = crate.get(f"#job-{job.id}-input-adapter-0")
    value = json.loads(adapter["value"])
    assert value["adapter_type"] == "PromoteDatasetToCollection"
    assert value["adapting"]["id"] == app.security.encode_id(dataset.id)
    assert adapter in crate.get(f"#galaxy-job-{job.id}")["object"]
    assert adapter["about"]["identifier"] == f"urn:uuid:{dataset.dataset.uuid}"


def test_ro_crate_job_parameter_values_are_withheld(tmp_path):
    app = _mock_app()
    _, _, _, output, job = _setup_simple_cat_job(app)
    job.parameters.append(model.JobParameter(name="threshold", value="10"))
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(output)
    crate = ROCrate(tmp_path)
    parameter = crate.get(f"#job-{job.id}-parameter-{len(job.parameters) - 1}")
    assert parameter.get("value") is None
    assert "credentials" in parameter["description"]


def test_ro_crate_unsafe_job_input_adapter_is_withheld(tmp_path):
    app = _mock_app()
    _, _, dataset, output, job = _setup_simple_cat_job(app)
    job.input_datasets[0].adapter = {"accessKey": "DO_NOT_EXPORT"}
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(output)
    metadata = (tmp_path / "ro-crate-metadata.json").read_text()
    assert "DO_NOT_EXPORT" not in metadata
    crate = ROCrate(tmp_path)
    assert "withheld" in crate.get(f"#job-{job.id}-input-adapter-0")["description"]


def test_ro_crate_job_metrics_use_compact_workflow_run_terms(tmp_path):
    app = _mock_app()
    _, _, _, output, job = _setup_simple_cat_job(app)
    job.add_metric("core", "runtime_seconds", 1.5)
    container = model.JobContainerAssociation(job=job, container_name="example/tool:1", container_type="docker")
    app.add_and_commit(container)

    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(output)

    metadata = json.loads((tmp_path / "ro-crate-metadata.json").read_text())
    context = metadata["@context"]
    assert "https://w3id.org/ro/terms/workflow-run/context" in (context if isinstance(context, list) else [context])
    action = next(entity for entity in metadata["@graph"] if entity["@id"] == f"#galaxy-job-{job.id}")
    assert "resourceUsage" in action
    assert "containerImage" in action
    assert not any(key.startswith(("http://", "https://")) for entity in metadata["@graph"] for key in entity)
    validate_with_roc_validator(crate_directory=tmp_path, profile="ro-crate-1.1")


def test_ro_crate_copy_provenance_is_serialized_before_attrs(tmp_path):
    app = _mock_app()
    _, history, input_dataset, output, _ = _setup_simple_cat_job(app)
    copied = model.HistoryDatasetAssociation(history=history, dataset=output.dataset, name="Copied output")
    copied.copied_from_history_dataset_association = output
    app.add_and_commit(copied)
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(copied)
    provenance = json.loads((tmp_path / "datasets_attrs.txt.provenance").read_text())
    assert len(provenance) == 2
    crate = ROCrate(tmp_path)
    assert any(entity.get("identifier") == f"urn:uuid:{input_dataset.dataset.uuid}" for entity in crate.get_entities())


def test_ro_crate_historical_job_input(tmp_path):
    app = _mock_app()
    _, _, dataset, _, job = _setup_simple_cat_job(app)
    previous_version = dataset.version
    original_name = dataset.name
    dataset.name = "Renamed after execution"
    app.commit()
    job.input_datasets[0].dataset_version = previous_version
    app.commit()
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(dataset)
        exporter.included_jobs[job.id] = job
    crate = ROCrate(tmp_path)
    action = crate.get(f"#galaxy-job-{job.id}")
    historical = next(value for value in action["object"] if value.id.startswith("#dataset-revision-"))
    assert historical["name"] == original_name
    assert historical["version"] == previous_version
    assert "not been reconstructed" in historical["conditionsOfAccess"]


def test_ro_crate_tool_lookup_failure_is_optional():
    writer = store.WriteCrates()
    lookup = Mock(side_effect=RuntimeError("unavailable"))
    writer.app = SimpleNamespace(toolbox=SimpleNamespace(get_tool=lookup))
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#tool", "@type": "SoftwareApplication"})
    writer._enrich_tool_entity(crate, entity, "example", "1")
    writer._enrich_tool_entity(crate, entity, "example", "1")
    lookup.assert_called_once()
    assert entity["softwareVersion"] == "1"
    assert entity.get("citation") is None


def test_ro_crate_embedded_integrity_uses_exported_bytes(tmp_path):
    app = _mock_app()
    _, _, dataset, _, _ = _setup_simple_cat_job(app)
    dataset.dataset.file_size = 999999
    dataset.dataset.hashes.append(model.DatasetHash(hash_function="SHA-256", hash_value="f" * 64))
    properties = store.WriteCrates._dataset_ro_crate_properties(dataset, dataset.get_file_name())
    assert properties["contentSize"] == str(os.path.getsize(dataset.get_file_name()))
    assert properties["_galaxy_sha256"] != "f" * 64
    assert not store.WriteCrates._valid_checksum("SHA-256", "not-a-hash")


def test_ro_crate_output_focus_survives_provenance_discovery(tmp_path):
    app = _mock_app()
    _, _, input_, output, job = _setup_simple_cat_job(app)
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(output)
    crate = ROCrate(tmp_path)
    assert crate.mainEntity["identifier"] == f"urn:uuid:{output.dataset.uuid}"
    assert crate.root_dataset["name"] == output.name
    attributes = json.loads((tmp_path / "datasets_attrs.txt.provenance").read_text())
    assert attributes, "Discovered provenance must also be serialized for Galaxy re-import"
    assert any(entity.get("identifier") == f"urn:uuid:{input_.dataset.uuid}" for entity in crate.get_entities())


def test_ro_crate_structured_values_preserve_order_and_missingness():
    from galaxy.model.store.ro_crate_utils import WorkflowRunCrateProfileBuilder

    builder = object.__new__(WorkflowRunCrateProfileBuilder)
    builder.model_store = store.WriteCrates()
    crate = ROCrate()
    value = builder._parameter_value(crate, "#value", "results", [False, 0, None])
    assert value.type == "Collection"
    assert [item["position"] for item in value["itemListElement"]] == [1, 2, 3]
    assert value["hasPart"][0]["value"] is False
    assert value["hasPart"][1]["value"] == 0
    assert "recorded" in value["hasPart"][2]["description"]
    secret = builder._parameter_value(crate, "#secret", "api_token", "secret")
    assert secret.get("value") is None
    assert "withheld" in secret["description"]


def test_get_export_dataset_filename_truncates_long_name():
    long_name = "https___example.com_" + "a" * 2000 + ".fastq.gz"
    filename = store.get_export_dataset_filename(long_name, "fastqsanger.gz", "abcdef1234567890", conversion_key=None)
    assert len(filename.encode("utf-8")) <= 255
    assert filename.endswith("_abcdef1234567890.fastqsanger.gz")

    filename_conv = store.get_export_dataset_filename(
        long_name, "bam", "abcdef1234567890", conversion_key="0123456789abcdef"
    )
    assert len(filename_conv.encode("utf-8")) <= 255
    assert filename_conv.endswith("_abcdef1234567890_conversion_0123456789abcdef.bam")


def test_import_export_history():
    """Test a simple job import/export after decompressing an archive (like history import/export tool)."""
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    imported_history = _import_export_history(app, h, export_files="copy")

    _assert_simple_cat_job_imported(imported_history)


def test_import_export_history_failed_job():
    """Test a simple job import/export, make sure state is maintained correctly."""
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app, state="error")

    imported_history = _import_export_history(app, h, export_files="copy")

    _assert_simple_cat_job_imported(imported_history, state="error")


def test_import_export_history_hidden_false_with_hidden_dataset():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)
    d2.visible = False
    app.commit()

    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=False)
    assert d1.dataset.get_size() == imported_history.datasets[0].get_size()
    assert imported_history.datasets[1].get_size() == 0


def test_import_export_history_hidden_true_with_hidden_dataset():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)
    d2.visible = False
    app.commit()

    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)
    assert d1.dataset.get_size() == imported_history.datasets[0].get_size()
    assert d2.dataset.get_size() == imported_history.datasets[1].get_size()


def test_import_export_history_allow_discarded_data():
    """Test an export and import without exporting dataset file data.

    Experimental state that should result in 'discarded' datasets that are not
    deleted.
    """
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    import_options = store.ImportOptions(
        discarded_data=store.ImportDiscardedDataType.ALLOW,
    )
    imported_history = _import_export_history(app, h, export_files=None, import_options=import_options)
    assert imported_history.name == "imported from archive: Test History"

    datasets = imported_history.datasets
    assert len(datasets) == 2
    assert datasets[0].state == datasets[1].state == model.Dataset.states.DISCARDED
    assert datasets[0].deleted is False

    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.state == "ok"
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset == datasets[1]


def setup_history_with_implicit_conversion():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    intermediate_ext = "bam"
    intermediate_implicit_hda = model.HistoryDatasetAssociation(
        extension=intermediate_ext, create_dataset=True, flush=False, history=h
    )
    intermediate_implicit_hda.hid = d2.hid
    convert_ext = "fasta"
    implicit_hda = model.HistoryDatasetAssociation(extension=convert_ext, create_dataset=True, flush=False, history=h)
    implicit_hda.hid = d2.hid
    # this adds and flushes the result...
    intermediate_implicit_hda.attach_implicitly_converted_dataset(app.model.context, implicit_hda, convert_ext)
    d2.attach_implicitly_converted_dataset(app.model.context, intermediate_implicit_hda, intermediate_ext)

    app.object_store.update_from_file(intermediate_implicit_hda.dataset, file_name=TEST_PATH_2_CONVERTED, create=True)
    app.object_store.update_from_file(implicit_hda.dataset, file_name=TEST_PATH_2_CONVERTED, create=True)

    assert len(h.active_datasets) == 4
    return app, h, implicit_hda


def test_import_export_history_with_implicit_conversion():
    app, h, _ = setup_history_with_implicit_conversion()
    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)

    assert len(imported_history.active_datasets) == 4
    recovered_hda_2 = imported_history.active_datasets[1]
    assert recovered_hda_2.implicitly_converted_datasets
    intermediate_conversion = recovered_hda_2.implicitly_converted_datasets[0]
    assert intermediate_conversion.type == "bam"
    intermediate_hda = intermediate_conversion.dataset
    assert intermediate_hda.implicitly_converted_datasets
    final_conversion = intermediate_hda.implicitly_converted_datasets[0]

    assert final_conversion.type == "fasta"
    assert final_conversion.dataset == imported_history.active_datasets[-1]

    # implicit conversions have the same HID... ensure this property is recovered...
    assert imported_history.active_datasets[2].hid == imported_history.active_datasets[1].hid


def test_import_export_history_with_implicit_conversion_parents_purged():
    app, h, implicit_hda = setup_history_with_implicit_conversion()
    # Purge parents
    parent = implicit_hda.implicitly_converted_parent_datasets[0].parent_hda
    parent.dataset.purged = True
    grandparent = parent.implicitly_converted_parent_datasets[0].parent_hda
    grandparent.dataset.purged = True
    app.model.context.commit()
    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)

    assert len(imported_history.active_datasets) == 2
    assert len(imported_history.datasets) == 4
    imported_implicit_hda = imported_history.active_datasets[1]
    assert imported_implicit_hda.extension == "fasta"

    # implicit conversions have the same HID... ensure this property is recovered...
    assert imported_implicit_hda.hid == implicit_hda.hid
    assert imported_implicit_hda.implicitly_converted_parent_datasets
    intermediate_implicit_conversion = imported_implicit_hda.implicitly_converted_parent_datasets[0]
    intermediate_hda = intermediate_implicit_conversion.parent_hda
    assert intermediate_hda.hid == implicit_hda.hid
    assert intermediate_hda.extension == "bam"
    assert intermediate_hda.implicitly_converted_datasets
    assert intermediate_hda.implicitly_converted_parent_datasets
    first_implicit_conversion = intermediate_hda.implicitly_converted_parent_datasets[0]
    source_hda = first_implicit_conversion.parent_hda
    assert source_hda.hid == implicit_hda.hid
    assert source_hda.extension == "txt"


def test_import_export_history_with_implicit_conversion_and_extra_files():
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    convert_ext = "fasta"
    implicit_hda = model.HistoryDatasetAssociation(extension=convert_ext, create_dataset=True, flush=False, history=h)
    implicit_hda.hid = d2.hid
    # this adds and flushes the result...
    d2.attach_implicitly_converted_dataset(app.model.context, implicit_hda, convert_ext)
    app.object_store.update_from_file(implicit_hda.dataset, file_name=TEST_PATH_2_CONVERTED, create=True)

    d2.dataset.create_extra_files_path()
    assert implicit_hda.dataset is not None
    implicit_hda.dataset.create_extra_files_path()

    app.write_primary_file(d2, "cool primary file 1")
    app.write_composite_file(d2, "cool composite file", "child_file")

    app.write_primary_file(implicit_hda, "cool primary file implicit")
    app.write_composite_file(implicit_hda, "cool composite file implicit", "child_file_converted")

    assert len(h.active_datasets) == 3
    imported_history = _import_export_history(app, h, export_files="copy", include_hidden=True)

    assert len(imported_history.active_datasets) == 3
    recovered_hda_2 = imported_history.active_datasets[1]
    assert recovered_hda_2.implicitly_converted_datasets
    imported_conversion = recovered_hda_2.implicitly_converted_datasets[0]
    assert imported_conversion.type == "fasta"
    assert imported_conversion.dataset == imported_history.active_datasets[2]

    # implicit conversions have the same HID... ensure this property is recovered...
    assert imported_history.active_datasets[2].hid == imported_history.active_datasets[1].hid

    _assert_extra_files_has_parent_directory_with_single_file_containing(
        imported_history.active_datasets[1], "child_file", "cool composite file"
    )

    _assert_extra_files_has_parent_directory_with_single_file_containing(
        imported_history.active_datasets[2], "child_file_converted", "cool composite file implicit"
    )


def test_import_export_bag_archive():
    """Test a simple job import/export using a BagIt archive."""
    dest_parent = mkdtemp()
    dest_export = os.path.join(dest_parent, "moo.tgz")

    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    with store.BagArchiveModelExportStore(
        dest_export, app=app, bag_archiver="tgz", export_files="copy"
    ) as export_store:
        export_store.export_history(h)

    model_store = store.BagArchiveImportModelStore(dest_export, app=app, user=u)
    with model_store.target_history(default_history=None) as imported_history:
        model_store.perform_import(imported_history)

    _assert_simple_cat_job_imported(imported_history)


def test_import_export_datasets():
    """Test a simple job import/export using a directory."""
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": False})
    u = h.user

    _perform_import_from_directory(temp_directory, app, u, import_history)

    datasets = import_history.datasets
    assert len(datasets) == 2
    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset == datasets[1]

    assert imported_job.input_datasets
    assert imported_job.input_datasets[0].dataset == datasets[0]


def test_import_from_dict():
    fixture_context = setup_fixture_context_with_history()
    import_dict = one_hda_model_store_dict()
    perform_import_from_store_dict(fixture_context, import_dict)
    import_history = fixture_context.history

    datasets = import_history.datasets
    assert len(datasets) == 1
    imported_hda = datasets[0]
    assert imported_hda.name == "my cool name"
    assert imported_hda.hid == 1
    # it wasn't deleted going in but we delete discarded datasets by default
    assert imported_hda.state == "deferred"
    assert not imported_hda.deleted

    assert imported_hda.dataset is not None
    assert len(imported_hda.dataset.hashes) == 1
    assert len(imported_hda.dataset.sources) == 1
    assert imported_hda.dataset.created_from_basename == "dataset.txt"
    imported_dataset_hash = imported_hda.dataset.hashes[0]
    imported_dataset_source = imported_hda.dataset.sources[0]
    assert imported_dataset_hash.hash_function == TEST_HASH_FUNCTION
    assert imported_dataset_hash.hash_value == TEST_HASH_VALUE
    assert imported_dataset_source.source_uri == TEST_SOURCE_URI


def test_import_library_from_dict():
    fixture_context = setup_fixture_context_with_history()
    import_dict = one_ld_library_model_store_dict()
    import_options = store.ImportOptions()
    import_options.allow_library_creation = True
    perform_import_from_store_dict(fixture_context, import_dict, import_options=import_options)

    sa_session = fixture_context.sa_session
    all_libraries = sa_session.scalars(select(model.Library)).all()
    assert len(all_libraries) == 1, len(all_libraries)
    all_lddas = sa_session.scalars(select(model.LibraryDatasetDatasetAssociation)).all()
    assert len(all_lddas) == 1, len(all_lddas)


def test_import_allow_discarded():
    fixture_context = setup_fixture_context_with_history()
    import_dict = one_hda_model_store_dict(include_source=False)
    import_options = store.ImportOptions(
        discarded_data=store.ImportDiscardedDataType.ALLOW,
    )
    perform_import_from_store_dict(fixture_context, import_dict, import_options=import_options)
    import_history = fixture_context.history
    datasets = import_history.datasets
    assert len(datasets) == 1
    imported_hda = datasets[0]
    assert imported_hda.name == "my cool name"
    assert imported_hda.hid == 1
    # it wasn't deleted going in but we delete discarded datasets by default
    assert imported_hda.state == "discarded"
    assert not imported_hda.deleted
    assert not imported_hda.metadata_deferred


def test_import_deferred_metadata():
    fixture_context = setup_fixture_context_with_history()
    import_dict = deferred_hda_model_store_dict(metadata_deferred=True)
    import_options = store.ImportOptions(
        discarded_data=store.ImportDiscardedDataType.ALLOW,
    )
    perform_import_from_store_dict(fixture_context, import_dict, import_options=import_options)
    import_history = fixture_context.history
    datasets = import_history.datasets
    assert len(datasets) == 1
    imported_hda = datasets[0]
    assert imported_hda.name == "my cool name"
    assert imported_hda.hid == 1
    # it wasn't deleted going in but we delete discarded datasets by default
    assert imported_hda.state == "deferred"
    assert not imported_hda.deleted
    assert imported_hda.metadata_deferred


def test_import_library_require_permissions():
    """Verify library creation (import) is off by default."""
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")

    library = model.Library(name="my library 1", description="my library description", synopsis="my synopsis")
    root_folder = model.LibraryFolder(name="my library 1", description="folder description")
    library.root_folder = root_folder
    sa_session.add_all((library, root_folder))
    app.commit()

    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app) as export_store:
        export_store.export_library(library)

    error_caught = False
    try:
        import_model_store = store.get_import_model_store_for_directory(temp_directory, app=app, user=u)
        import_model_store.perform_import()
    except AssertionError:
        # TODO: throw and catch a better exception...
        error_caught = True

    assert error_caught


def test_import_export_library(tmp_path):
    """Test basics of library, library folder, and library dataset import/export."""
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")

    library = model.Library(name="my library 1", description="my library description", synopsis="my synopsis")
    root_folder = model.LibraryFolder(name="my library 1", description="folder description")
    library.root_folder = root_folder
    sa_session.add_all((library, root_folder))
    app.commit()

    subfolder = model.LibraryFolder(name="sub folder 1", description="sub folder")
    root_folder.add_folder(subfolder)
    sa_session.add(subfolder)

    ld = model.LibraryDataset(folder=root_folder, name="my name", info="my library dataset")
    ldda = model.LibraryDatasetDatasetAssociation(create_dataset=True, flush=False)
    ld.library_dataset_dataset_association = ldda
    root_folder.add_library_dataset(ld)

    sa_session.add(ld)
    sa_session.add(ldda)

    app.commit()
    assert len(root_folder.datasets) == 1
    assert len(root_folder.folders) == 1

    with store.DirectoryModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_library(library)

    import_model_store = store.get_import_model_store_for_directory(
        tmp_path, app=app, user=u, import_options=store.ImportOptions(allow_library_creation=True)
    )
    import_model_store.perform_import()

    all_libraries = sa_session.scalars(select(model.Library)).all()
    assert len(all_libraries) == 2, len(all_libraries)
    all_lddas = sa_session.scalars(select(model.LibraryDatasetDatasetAssociation)).all()
    assert len(all_lddas) == 2, len(all_lddas)

    new_library = [lib for lib in all_libraries if lib.id != library.id][0]
    assert new_library.name == "my library 1"
    assert new_library.description == "my library description"
    assert new_library.synopsis == "my synopsis"

    new_root = new_library.root_folder
    assert new_root
    assert new_root.name == "my library 1"

    assert len(new_root.folders) == 1
    assert len(new_root.datasets) == 1


def test_import_export_invocation():
    app = _mock_app()
    workflow_invocation = _setup_invocation(app)
    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)

    sa_session = app.model.context
    h2 = model.History(user=workflow_invocation.user)
    sa_session.add(h2)
    app.commit()

    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, app=app, user=workflow_invocation.user, import_options=store.ImportOptions()
    )
    import_model_store.perform_import(history=h2)


def validate_crate_metadata(as_dict):
    context = as_dict["@context"]
    if isinstance(context, str):
        context = [context]
    assert "https://w3id.org/ro/crate/1.1/context" in context


def validate_has_pl_galaxy(ro_crate: ROCrate):
    programming_language = ro_crate.mainEntity.get("programmingLanguage")
    assert programming_language
    assert programming_language.id == "https://w3id.org/workflowhub/workflow-ro-crate#galaxy"
    assert programming_language.name == "Galaxy"
    assert getattr(programming_language.url, "id", programming_language.url) == "https://galaxyproject.org/"


def validate_organize_action(ro_crate: ROCrate):
    organize_action = next((x for x in ro_crate.contextual_entities if x.type == "OrganizeAction"), None)
    assert organize_action


def validate_has_mit_license(ro_crate: ROCrate):
    assert ro_crate.mainEntity["license"] == "MIT"
    assert ro_crate.root_dataset["license"].id == "#license-not-specified"


def validate_creators(ro_crate: ROCrate):
    """
    Validate that creators (Person and Organization) are correctly added.
    """
    creators = ro_crate.mainEntity.get("creator")
    assert creators, "No creators found in the RO-Crate"

    for creator in creators:
        assert creator["@type"] in {"Person", "Organization"}
        if creator["@type"] == "Person":
            assert "name" in creator
            assert "orcid" in creator or "identifier" in creator
        elif creator["@type"] == "Organization":
            assert "name" in creator
            assert "url" in creator


def validate_steps(ro_crate: ROCrate):
    """
    Validate that workflow steps (HowToStep) are correctly added.
    """
    steps = ro_crate.mainEntity.get("step")
    assert steps, "No steps found in the RO-Crate"

    for i, step in enumerate(steps, start=1):
        assert step["@type"] == "HowToStep"
        assert step["position"] == i
        assert "name" in step
        assert "description" in step or step["description"] is None


def validate_tools(ro_crate: ROCrate):
    """
    Validate that tools (SoftwareApplication) are correctly added.
    """
    tools = ro_crate.mainEntity.get("hasPart")
    assert tools, "No tools found in the RO-Crate"

    tool_ids = set()
    for tool in tools:
        assert tool["@type"] == "SoftwareApplication"
        assert "name" in tool
        assert "softwareVersion" in tool
        assert "version" not in tool
        assert "description" in tool or tool["description"] is None
        assert tool.id not in tool_ids, "Duplicate tool found"
        tool_ids.add(tool.id)


def validate_has_readme(ro_crate: ROCrate):
    found_readme = False
    for e in ro_crate.get_entities():
        if e.id == "README.md":
            assert e.type == "File"
            assert e["encodingFormat"] == "text/markdown"
            # assert e["about"] == "./"
            found_readme = True
    assert found_readme


def open_ro_crate(crate_directory):
    metadata_json_path = crate_directory / "ro-crate-metadata.json"
    with metadata_json_path.open() as f:
        metadata_json = json.load(f)
    validate_crate_metadata(metadata_json)
    crate = ROCrate(crate_directory)
    return crate


def validate_history_crate_directory(crate_directory):
    # first validate against the base RO-Crate spec
    validate_with_roc_validator(crate_directory=crate_directory, profile="ro-crate-1.1")

    # then do Galaxy-specific validation
    crate = open_ro_crate(crate_directory)
    validate_has_readme(crate)
    assert crate.name == "Test History"
    assert crate.root_dataset["identifier"].startswith("galaxy-history:")
    assert crate.root_dataset["dateCreated"]
    assert crate.root_dataset["dateModified"]
    assert crate.root_dataset["license"].id == "#license-not-specified"
    export_scope = next(
        item for item in crate.root_dataset["additionalProperty"] if item["name"] == "Galaxy export scope"
    )
    assert "generatedAt" not in json.loads(export_scope["value"])

    datasets = [entity for entity in crate.data_entities if entity.id.startswith("datasets/")]
    assert len(datasets) == 2
    for dataset in datasets:
        assert dataset["identifier"].startswith("urn:uuid:")
        assert dataset["encodingFormat"] == "text/plain"
        assert int(dataset["contentSize"]) > 0
        assert dataset["dateCreated"]
        assert dataset["dateModified"]
        checksum = dataset["additionalProperty"]
        checksum = checksum[0] if isinstance(checksum, list) else checksum
        assert checksum["name"] == "SHA-256"
        assert len(checksum["value"]) == 64

    associations = [
        entity for entity in crate.contextual_entities if entity.id.startswith("#galaxy-HistoryDatasetAssociation-")
    ]
    assert len(associations) == 2
    payload_identifiers = {dataset["identifier"] for dataset in datasets}
    for association in associations:
        assert association.type == "CreativeWork"
        assert association["identifier"] == association.id[1:]
        assert association["identifier"] not in payload_identifiers
        assert association["about"] in datasets

    job_actions = [entity for entity in crate.contextual_entities if entity.id.startswith("#galaxy-job-")]
    assert len(job_actions) == 1
    assert len(job_actions[0]["object"]) == 1
    assert len(job_actions[0]["result"]) == 1
    assert job_actions[0]["instrument"]["softwareVersion"]

    history_metadata = crate.get("history_attrs.txt")
    assert history_metadata
    assert history_metadata.type == "File"
    assert history_metadata["encodingFormat"] == "application/json"


def validate_main_entity(ro_crate: ROCrate):
    workflow = ro_crate.mainEntity
    assert workflow
    assert workflow.id.endswith(".gxwf.yml")
    assert workflow["name"]
    assert workflow["name"] == "Test Workflow"
    assert "SoftwareSourceCode" in workflow.type
    assert "ComputationalWorkflow" in workflow.type
    assert len(workflow["input"]) == 1
    assert len(workflow["output"]) == 1


def validate_create_action(ro_crate: ROCrate):
    workflow = ro_crate.mainEntity
    actions = [_ for _ in ro_crate.contextual_entities if "CreateAction" in _.type]
    assert actions
    wf_action = next(action for action in actions if action.get("instrument") is workflow)
    assert wf_action["instrument"]
    assert wf_action["instrument"] is workflow
    assert wf_action.id.startswith(("urn:uuid:", "#workflow-run-"))
    assert wf_action["startTime"]
    assert wf_action["startTime"].endswith("+00:00")
    # These fixtures do not record an invocation completion time.
    assert wf_action.get("endTime") is None
    assert wf_action.get("actionStatus") is None
    wf_objects = wf_action["object"]
    wf_results = wf_action["result"]
    assert len(wf_objects) == 1
    assert len(wf_results) == 1
    for entity in wf_results:
        if entity.id.endswith(".txt"):
            assert "File" in entity.type
            wf_output_file = entity
            assert wf_output_file["encodingFormat"] == "text/plain"
            examples = wf_output_file["exampleOfWork"]
            assert workflow["output"][0] in (examples if isinstance(examples, list) else [examples])


def validate_other_entities(ro_crate: ROCrate):
    workflow = ro_crate.mainEntity
    inputs = workflow["input"]
    outputs = workflow["output"]
    assert inputs[0]["additionalType"] == "File"
    assert outputs[0]["additionalType"] == "File"

    for entity in inputs + outputs:
        assert "FormalParameter" in entity.type

    sel = [_ for _ in ro_crate.contextual_entities if "OrganizeAction" in _.type]
    assert len(sel) == 1
    engine_action = sel[0]
    assert "SoftwareApplication" in engine_action["instrument"].type
    assert engine_action["instrument"].get("softwareVersion") is None
    assert engine_action["instrument"]["additionalProperty"]
    assert "CreateAction" in engine_action["result"].type


def validate_invocation_crate_directory(crate_directory):
    # first validate against the Workflow Run Crate profile
    validate_with_roc_validator(crate_directory=crate_directory, profile="workflow-run-crate-0.5")
    crate = open_ro_crate(crate_directory)
    declared_profiles = {profile.id for profile in crate.root_dataset["conformsTo"]}
    if "https://w3id.org/ro/wfrun/provenance/0.5" in declared_profiles:
        validate_with_roc_validator(crate_directory=crate_directory, profile="provenance-run-crate-0.5")
        controls = [entity for entity in crate.contextual_entities if "ControlAction" in entity.type]
        assert controls
        assert all("CreateAction" in control["object"].type for control in controls)

    # then do Galaxy-specific validation
    validate_main_entity(crate)
    validate_create_action(crate)
    validate_other_entities(crate)
    validate_has_pl_galaxy(crate)
    validate_organize_action(crate)
    validate_has_mit_license(crate)
    validate_creators(crate)
    validate_steps(crate)
    validate_tools(crate)
    validate_has_readme(crate)
    assert crate.root_dataset["publisher"].type == "Organization"
    assert crate.root_dataset["author"].type == "Organization"
    assert crate.root_dataset["sdPublisher"]["publisher"].type == "Organization"
    assert crate.root_dataset["sdPublisher"]["softwareVersion"]
    assert crate.mainEntity["identifier"].startswith("urn:uuid:")
    assert crate.mainEntity["encodingFormat"] == "application/yaml"
    assert any("bioschemas.org/profiles/ComputationalWorkflow" in item.id for item in crate.mainEntity["conformsTo"])
    assert crate.mainEntity["additionalProperty"]
    workflow_action = next(
        entity
        for entity in crate.contextual_entities
        if "CreateAction" in entity.type and entity.get("instrument") is crate.mainEntity
    )
    assert workflow_action["agent"].type == "Person"
    assert "email" not in workflow_action["agent"]
    for entity in crate.contextual_entities:
        if entity.id.startswith("#job-"):
            assert entity.get("value") is None
            assert "withheld" in entity["description"]


def validate_invocation_collection_crate_directory(crate_directory):
    # first validate against the Workflow Run Crate profile
    validate_with_roc_validator(crate_directory=crate_directory, profile="workflow-run-crate-0.5")

    # then do Galaxy-specific validation
    ro_crate = open_ro_crate(crate_directory)
    workflow = ro_crate.mainEntity
    root = ro_crate.root_dataset
    actions = [_ for _ in ro_crate.contextual_entities if "CreateAction" in _.type]
    assert actions
    wf_action = next(action for action in actions if action.get("instrument") is workflow)
    assert wf_action in root["mentions"]
    assert len(workflow["input"]) == 2
    assert len(workflow["output"]) == 1
    assert len(root["mentions"]) >= 4
    collections = [_ for _ in ro_crate.contextual_entities if "Collection" in _.type]
    assert len(collections) == 3
    collection = collections[0]
    assert collection.type == "Collection"
    assert collection["additionalType"] == "https://galaxyproject.org/collection/list"
    assert len(collection["hasPart"]) == 2
    for dataset in collection["hasPart"]:
        assert dataset in root["hasPart"]


def validate_with_roc_validator(crate_directory, profile):
    settings = services.ValidationSettings(
        rocrate_uri=crate_directory,
        profile_identifier=profile,
        requirement_severity=models.Severity.REQUIRED,
        abort_on_first=False,  # do not stop on first issue
    )

    result = services.validate(settings)

    issues = result.get_issues()
    assert len(issues) == 0, f"RO-Crate is invalid: {[issue.message for issue in issues]}"


def test_export_history_with_missing_hid(tmp_path):
    # The dataset's hid was used to compose the file name during the export but it
    # can be missing sometimes. We now use the dataset's encoded id instead.
    app = _mock_app()
    u, history, d1, d2, j = _setup_simple_cat_job(app)

    # Remove hid from d1
    d1.hid = None
    app.commit()

    with store.DirectoryModelExportStore(tmp_path, app=app, export_files="copy") as export_store:
        export_store.export_history(history)


def test_export_history_to_ro_crate(tmp_path):
    app = _mock_app()
    u, history, d1, d2, j = _setup_simple_cat_job(app)

    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_history(history)
    validate_history_crate_directory(tmp_path)


def test_failed_job_status_in_history_ro_crate(tmp_path):
    app = _mock_app()
    u, history, d1, d2, job = _setup_simple_cat_job(app, state="error")
    job.info = "Tool execution failed"
    app.commit()

    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_history(history)

    crate = open_ro_crate(tmp_path)
    action = next(entity for entity in crate.contextual_entities if entity.id.startswith("#galaxy-job-"))
    assert action["actionStatus"] == "http://schema.org/FailedActionStatus"
    assert action["error"] == "Tool execution failed"


def test_export_single_dataset_to_ro_crate(tmp_path):
    app = _mock_app()
    u, history, dataset, output, job = _setup_simple_cat_job(app)

    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.add_dataset(dataset)

    validate_with_roc_validator(crate_directory=tmp_path, profile="ro-crate-1.1")
    crate = open_ro_crate(tmp_path)
    assert crate.root_dataset["mainEntity"]["identifier"].startswith("urn:uuid:")
    checksum = crate.root_dataset["mainEntity"]["additionalProperty"]
    checksum = checksum[0] if isinstance(checksum, list) else checksum
    assert checksum["name"] == "SHA-256"


def test_ro_crate_scientific_metadata_and_primary_hash(tmp_path):
    app = _mock_app()
    _, history, dataset, _, _ = _setup_simple_cat_job(app)
    dataset.dbkey = "hg38"
    dataset.dataset.hashes.append(
        model.DatasetHash(hash_function="SHA-256", hash_value="component-hash", extra_files_path="component.txt")
    )
    dataset.dataset.hashes.append(model.DatasetHash(hash_function="MD5", hash_value="a" * 32))
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.add_dataset(dataset)
    crate = ROCrate(tmp_path)
    properties = {item["name"]: item["value"] for item in crate.mainEntity["additionalProperty"]}
    assert properties["SHA-256"] != "component-hash"
    assert len(properties["SHA-256"]) == 64
    assert properties["Recorded source checksum (MD5; not verified against exported bytes)"] == "a" * 32
    assert properties["Galaxy dbkey"] == "hg38"


def test_ro_crate_scientific_metadata_is_discovered_dynamically():
    writer = store.WriteCrates()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#dataset", "@type": "Dataset"})
    writer._add_scientific_metadata(
        crate,
        entity,
        {"future_datatype_field": {"score": 7}, "index_file": "/private/index"},
    )
    properties = {item["name"]: item["value"] for item in entity["additionalProperty"]}
    assert json.loads(properties["Galaxy future_datatype_field"]) == {"score": 7}
    assert "Galaxy index_file" not in properties


def test_ro_crate_scientific_metadata_skips_array_values_and_private_fields():
    import numpy

    writer = store.WriteCrates()
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#dataset", "@type": "Dataset"})
    writer._add_scientific_metadata(
        crate,
        entity,
        {
            "array_value": numpy.array([1, 2]),
            "future_datatype_field": {"score": 7},
            "apiKey": "marker",
            "nested": {"secret": "marker"},
        },
    )
    properties = {item["name"]: item["value"] for item in entity["additionalProperty"]}
    assert properties == {"Galaxy future_datatype_field": '{"score": 7}'}


def test_ro_crate_property_rejects_private_field_names_and_arrays():
    import numpy

    writer = store.WriteCrates()
    crate = ROCrate()
    writer._add_metadata_property(crate, crate.root_dataset, "API token", "marker")
    writer._add_metadata_property(crate, crate.root_dataset, "Nested", {"password": "marker"})
    writer._add_metadata_property(crate, crate.root_dataset, "Array", numpy.array([1, 2]))
    assert not crate.root_dataset.get("additionalProperty")


def test_ro_crate_invocation_metadata_only_dataset(tmp_path):
    from galaxy.model.store.ro_crate_utils import WorkflowRunCrateProfileBuilder

    app = _mock_app()
    _, _, dataset, _, _ = _setup_simple_cat_job(app)
    writer = store.WriteCrates()
    writer.dataset_id_to_path = {}
    writer.export_directory = tmp_path
    builder = object.__new__(WorkflowRunCrateProfileBuilder)
    builder.model_store = writer
    builder.file_entities = {}
    crate = ROCrate()
    entity = builder._add_file(dataset, {}, crate)
    assert entity.type == "Dataset"
    assert entity.id == f"#dataset-{dataset.dataset.uuid}"
    assert entity["identifier"] == f"urn:uuid:{dataset.dataset.uuid}"
    assert entity in crate.root_dataset["hasPart"]
    assert builder._add_file(dataset, {}, crate) is entity


def test_ro_crate_instance_operator():
    writer = store.WriteCrates()
    writer.app = SimpleNamespace(
        config=SimpleNamespace(
            organization_name="Example University",
            organization_url="https://example.org",
            ga4gh_service_id="org.example.galaxy",
            brand="Research Galaxy",
        )
    )
    crate = ROCrate()
    writer._add_instance_metadata(crate)
    assert crate.root_dataset["publisher"]["name"] == "Example University"
    assert crate.root_dataset["publisher"]["url"] == "https://example.org"


def test_ro_crate_repeated_dataset_ports(tmp_path):
    from galaxy.model.store.ro_crate_utils import WorkflowRunCrateProfileBuilder

    app = _mock_app()
    _, _, dataset, _, _ = _setup_simple_cat_job(app)
    inputs = [
        SimpleNamespace(dataset=dataset, workflow_step_id=index, workflow_step=SimpleNamespace(label=f"input {index}"))
        for index in (1, 2)
    ]
    invocation = SimpleNamespace(id=1, input_datasets=inputs, output_datasets=[])
    writer = store.WriteCrates()
    writer.dataset_id_to_path = {}
    writer.export_directory = tmp_path
    writer.included_invocations = [invocation]
    builder = object.__new__(WorkflowRunCrateProfileBuilder)
    builder.model_store = writer
    builder.invocation = invocation
    builder.file_entities = {}
    crate = ROCrate()
    crate.mainEntity = crate.add_jsonld({"@id": "#workflow", "@type": "ComputationalWorkflow"})
    builder.create_action = crate.add_jsonld({"@id": "#run", "@type": "CreateAction"})
    builder._add_files(crate)
    assert len(crate.mainEntity["input"]) == 2
    entity = builder.file_entities[dataset.dataset.id]
    assert len(entity["exampleOfWork"]) == 2
    assert {parameter["name"] for parameter in entity["exampleOfWork"]} == {"input 1", "input 2"}


def test_ro_crate_source_hashes_and_transforms():
    writer = store.WriteCrates()
    source = SimpleNamespace(
        source_uri="https://example.org/data",
        hashes=[SimpleNamespace(hash_function="SHA-256", hash_value="a" * 64)],
        transform=[{"action": "to_posix_lines"}],
        requested_transform=None,
    )
    private_source = SimpleNamespace(source_uri="https://example.org/private?token=secret")
    dataset = SimpleNamespace(
        metadata=SimpleNamespace(), dataset=SimpleNamespace(hashes=[], sources=[source, private_source])
    )
    crate = ROCrate()
    entity = crate.add_jsonld({"@id": "#dataset", "@type": "Dataset"})
    writer._attach_dataset_metadata(crate, entity, dataset)
    assert len(entity["isBasedOn"]) == 1
    assert entity["isBasedOn"][0]["additionalProperty"][0]["value"] == "a" * 64
    assert json.loads(entity["isBasedOn"][0]["additionalProperty"][1]["value"]) == [{"action": "to_posix_lines"}]


def test_ro_crate_scalar_outputs_preserve_types():
    from galaxy.model.store.ro_crate_utils import WorkflowRunCrateProfileBuilder

    builder = object.__new__(WorkflowRunCrateProfileBuilder)
    builder.model_store = store.WriteCrates()
    builder.invocation = SimpleNamespace(
        id=1,
        steps=[],
        output_values=[
            SimpleNamespace(value=False, workflow_output=SimpleNamespace(id=1, label="passed", output_name="result")),
            SimpleNamespace(
                value="secret", workflow_output=SimpleNamespace(id=2, label="api_token", output_name="token")
            ),
        ],
    )
    crate = ROCrate()
    crate.mainEntity = crate.add_jsonld({"@id": "#workflow", "@type": "ComputationalWorkflow"})
    builder.create_action = crate.add_jsonld({"@id": "#run", "@type": "CreateAction"})
    builder._add_parameters(crate)
    assert len(crate.mainEntity["output"]) == 2
    assert crate.mainEntity["output"][0]["additionalType"] == "Boolean"
    assert builder.create_action["result"][0]["value"] is False
    assert builder.create_action["result"][1].get("value") is None
    assert "withheld" in builder.create_action["result"][1]["description"]


def test_export_dataset_collection_to_ro_crate(tmp_path):
    app = _mock_app()
    u, history, c1, c2, c3, hc1, hc2, hc3, job = _setup_simple_collection_job(app)

    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_collection(hc1)

    validate_with_roc_validator(crate_directory=tmp_path, profile="ro-crate-1.1")
    crate = open_ro_crate(tmp_path)
    collection = crate.root_dataset["mainEntity"]
    assert collection.type == "Collection"
    assert [item["name"] for item in collection["itemListElement"]] == ["forward", "reverse"]
    assert [item["position"] for item in collection["itemListElement"]] == [1, 2]


def test_ro_crate_history_respects_include_deleted_collections(tmp_path):
    app = _mock_app()
    _, history, collection, _, _, association, _, _, _ = _setup_simple_collection_job(app)
    association.deleted = True
    app.commit()
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.export_history(history, include_deleted=True)
    crate = ROCrate(tmp_path)
    entity = crate.get(f"#dataset-collection-{collection.id}")
    assert entity is not None
    assert entity["identifier"] == association.type_id


def test_export_invocation_to_ro_crate(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_invocation(app)
    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    validate_invocation_crate_directory(tmp_path)


def test_ro_crate_workflow_connections(tmp_path):
    app = _mock_app()
    invocation = _setup_invocation(app)
    source, target = invocation.workflow.steps
    input_ = model.WorkflowStepInput(target)
    input_.name = "input1"
    input_.merge_type = "merge_flattened"
    connection = model.WorkflowStepConnection()
    connection.output_step = source
    connection.output_name = "output"
    connection.input_step_input = input_
    app.add_and_commit(connection)
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.export_workflow_invocation(invocation)
    crate = ROCrate(tmp_path)
    edge = crate.get(f"#parameter-connection-{connection.id}")
    assert edge["sourceParameter"] in crate.mainEntity["input"]
    receiver = crate.get(f"#workflow-step-{target.id}")
    assert edge in receiver["connection"]
    assert edge["targetParameter"] in receiver["workExample"]["input"]
    assert crate.mainEntity["connection"][0]["targetParameter"] in crate.mainEntity["output"]
    validate_with_roc_validator(crate_directory=tmp_path, profile="provenance-run-crate-0.5")


def test_ro_crate_workflow_privacy_execution_version_and_diagnostics(tmp_path):
    app = _mock_app()
    invocation = _setup_invocation(app)
    job = invocation.steps[1].job
    job.galaxy_version = "23.2"
    container = model.JobContainerAssociation(job=job, container_name="example/tool:1", container_type="docker")
    app.add_and_commit(container)
    invocation.workflow.readme = "credentials at https://example.org/data?token=DO_NOT_EXPORT"
    invocation.workflow.logo_url = "https://example.org/logo?token=DO_NOT_EXPORT"
    invocation.workflow.creator_metadata = [
        {
            "class": "Person",
            "name": "Researcher",
            "identifier": "https://example.org/person?token=DO_NOT_EXPORT",
            "url": "https://example.org/person?token=DO_NOT_EXPORT",
        }
    ]
    message = model.WorkflowInvocationMessage(
        workflow_invocation=invocation,
        reason="dataset_failed",
        workflow_step_id=invocation.steps[1].workflow_step_id,
        job_id=job.id,
        hda_id=job.output_datasets[0].dataset.id,
        details="A dataset failed validation",
    )
    app.add_and_commit(message)
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.export_workflow_invocation(invocation)
    crate = ROCrate(tmp_path)
    metadata_text = (tmp_path / "ro-crate-metadata.json").read_text()
    assert "DO_NOT_EXPORT" not in metadata_text
    engine = crate.get(f"urn:galaxy:workflow-engine:{invocation.uuid or invocation.id}")
    assert engine["softwareVersion"] == "23.2"
    job_action = crate.get(f"#galaxy-job-{job.id}")
    image = job_action["containerImage"]
    assert image.type == "https://w3id.org/ro/terms/workflow-run#ContainerImage"
    assert job_action["instrument"]["softwareVersion"] == job.tool_version
    assert job_action.get("softwareVersion") is None
    action_metadata = {
        value["name"]: value["value"] for value in job_action["additionalProperty"] if value.get("value")
    }
    assert action_metadata["Recorded Galaxy execution version"] == "23.2"
    # This is the publication date of the crate metadata, not of the workflow.
    root_metadata = next(entity for entity in json.loads(metadata_text)["@graph"] if entity["@id"] == "./")
    assert root_metadata["datePublished"]
    assert not any(
        entity.get("name") == "Galaxy crate generation time" for entity in json.loads(metadata_text)["@graph"]
    )
    diagnostic = crate.get(f"#invocation-message-{message.id}")
    assert crate.get(f"#galaxy-job-{job.id}") in diagnostic["about"]
    assert crate.get(f"#workflow-step-{invocation.steps[1].workflow_step_id}") in diagnostic["about"]


def test_ro_crate_nested_workflow_without_file_digest(tmp_path, monkeypatch):
    import hashlib

    monkeypatch.delattr(hashlib, "file_digest", raising=False)
    app = _mock_app()
    parent = _setup_invocation(app)
    parent.user.email = "parent@example.com"
    app.commit()
    child = _setup_invocation(app)
    step = model.WorkflowStep()
    step.type = "subworkflow"
    step.order_index = 2
    step.subworkflow = child.workflow
    parent.workflow.steps.append(step)
    execution = model.WorkflowInvocationStep()
    execution.workflow_step = step
    parent.steps.append(execution)
    association = model.WorkflowInvocationToSubworkflowInvocationAssociation(
        parent_workflow_invocation=parent, workflow_step=step, subworkflow_invocation=child
    )
    app.add_and_commit(step, execution, association)
    with store.ROCrateModelExportStore(tmp_path, app=app) as exporter:
        exporter.export_workflow_invocation(parent)
    crate = ROCrate(tmp_path)
    nested = next(
        entity for entity in crate.get_entities() if entity.get("identifier") == f"urn:uuid:{child.workflow.uuid}"
    )
    assert "ComputationalWorkflow" in nested.type
    assert "File" in nested.type
    assert any(prop["name"] == "SHA-256" for prop in nested["additionalProperty"])
    validate_with_roc_validator(crate_directory=tmp_path, profile="workflow-run-crate-0.5")


def test_export_simple_invocation_to_ro_crate(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_simple_invocation(app)
    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    validate_invocation_crate_directory(tmp_path)


def test_export_collection_invocation_to_ro_crate(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_collection_invocation(app)
    with store.ROCrateModelExportStore(tmp_path, app=app) as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    validate_invocation_collection_crate_directory(tmp_path)


def test_export_invocation_to_ro_crate_archive(tmp_path):
    app = _mock_app()
    workflow_invocation = _setup_invocation(app)

    crate_zip = tmp_path / "crate.zip"
    crate_directory = tmp_path / "crate"
    with store.ROCrateArchiveModelExportStore(crate_zip, app=app, export_files="symlink") as export_store:
        export_store.export_workflow_invocation(workflow_invocation)
    with CompressedFile(crate_zip) as compressed_file:
        assert compressed_file.file_type == "zip"
        compressed_file.extract(crate_directory)
    validate_invocation_crate_directory(crate_directory)


def test_finalize_job_state():
    """Verify jobs are given finalized states on import."""
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": False})
    u = h.user

    with open(os.path.join(temp_directory, store.ATTRS_FILENAME_JOBS)) as f:
        job_attrs = json.load(f)

    for job in job_attrs:
        job["state"] = "queued"

    with open(os.path.join(temp_directory, store.ATTRS_FILENAME_JOBS), "w") as f:
        json.dump(job_attrs, f)

    _perform_import_from_directory(temp_directory, app, u, import_history)

    datasets = import_history.datasets
    assert len(datasets) == 2
    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.state == model.Job.states.ERROR


def test_import_traceback_handling():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": False})
    u = h.user
    traceback_message = "Oh no, a traceback here!!!"

    with open(os.path.join(temp_directory, store.TRACEBACK), "w") as f:
        f.write(traceback_message)

    with pytest.raises(store.FileTracebackException) as exc:
        _perform_import_from_directory(temp_directory, app, u, import_history)
    assert exc.value.traceback == traceback_message


def test_export_history_with_orphan_icjja(tmp_path):
    """Orphan ImplicitCollectionJobsJobAssociation rows (job_id NULL) are
    persisted by the import path when an ICJ references a job key not in
    object_import_tracker.jobs_by_key. The next export crashes in
    get_identifier(j_a.job=None); ignore_errors skips the orphan."""
    app = _mock_app()
    u, h, _d1, _d2, j = _setup_simple_cat_job(app)

    icj = model.ImplicitCollectionJobs()
    linked = model.ImplicitCollectionJobsJobAssociation()
    linked.order_index = 0
    linked.implicit_collection_jobs = icj
    linked.job = j
    to_orphan = model.ImplicitCollectionJobsJobAssociation()
    to_orphan.order_index = 1
    to_orphan.implicit_collection_jobs = icj
    to_orphan.job = j
    app.add_and_commit(icj, linked, to_orphan)

    # Mimic the post-import state: drop the FK so the row becomes an orphan.
    to_orphan.job = None  # type: ignore[assignment]
    app.commit()

    with pytest.raises(AttributeError):
        with store.TarModelExportStore(str(tmp_path / "strict.tgz"), app=app, export_files="copy") as export_store:
            export_store.export_history(h)

    tolerant_archive = str(tmp_path / "tolerant.tgz")
    with store.TarModelExportStore(tolerant_archive, app=app, export_files="copy", ignore_errors=True) as export_store:
        export_store.export_history(h)

    imported_history = import_archive(tolerant_archive, app, u)
    imported_job = imported_history.datasets[1].creating_job
    imported_icj = imported_job.implicit_collection_jobs_association.implicit_collection_jobs
    assert len(imported_icj.jobs) == 1


def test_export_history_with_null_param_id(tmp_path):
    """Job params shaped {"src": "hda"|"hdca"|"dce", "id": null} are persisted
    by the import path at model/store/__init__.py:1860-1888 when a referenced
    HDA/HDCA/DCE can't be resolved. Strict export raises in
    get_identifier_for_id; ignore_errors passes the null through.

    Reproducing the on-disk state directly: the only producer is the import
    path itself, so deleting the referenced HDA wouldn't null the persisted
    param JSON."""
    app = _mock_app()
    u, h, _d1, _d2, j = _setup_simple_cat_job(app)
    j.parameters = [model.JobParameter(name="input1", value=json.dumps({"src": "hda", "id": None}))]
    app.commit()

    with pytest.raises(NotImplementedError):
        with store.TarModelExportStore(str(tmp_path / "strict.tgz"), app=app, export_files="copy") as export_store:
            export_store.export_history(h)

    tolerant_archive = str(tmp_path / "tolerant.tgz")
    with store.TarModelExportStore(tolerant_archive, app=app, export_files="copy", ignore_errors=True) as export_store:
        export_store.export_history(h)

    imported_history = import_archive(tolerant_archive, app, u)
    imported_job = imported_history.datasets[1].creating_job
    assert json.loads(imported_job.raw_param_dict()["input1"]) == {"src": "hda", "id": None}


def test_import_export_edit_datasets():
    """Test modifying existing HDA and dataset metadata with import."""
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    u = h.user

    # Fabric editing metadata...
    datasets_metadata_path = os.path.join(temp_directory, store.ATTRS_FILENAME_DATASETS)
    with open(datasets_metadata_path) as f:
        datasets_metadata = json.load(f)

    datasets_metadata[0]["name"] = "my new name 0"
    datasets_metadata[1]["name"] = "my new name 1"

    assert "dataset" in datasets_metadata[0]
    datasets_metadata[0]["dataset"]["object_store_id"] = "foo1"

    with open(datasets_metadata_path, "w") as f:
        json.dump(datasets_metadata, f)

    _perform_import_from_directory(temp_directory, app, u, import_history, store.ImportOptions(allow_edit=True))

    datasets = import_history.datasets
    assert len(datasets) == 0

    d1 = h.datasets[0]
    d2 = h.datasets[1]

    assert d1.name == "my new name 0", d1.name
    assert d2.name == "my new name 1", d2.name
    assert d1.dataset.object_store_id == "foo1", d1.dataset.object_store_id


def test_import_export_edit_collection(tmp_path):
    """Test modifying existing collections with imports."""
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    c1 = model.DatasetCollection(collection_type="list", populated=False)
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=1, collection=c1, name="HistoryCollectionTest1")

    sa_session.add(hc1)
    sa_session.add(h)
    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)

    with store.DirectoryModelExportStore(tmp_path, app=app, for_edit=True) as export_store:
        export_store.add_dataset_collection(hc1)

    # Fabric editing metadata for collection...
    collections_metadata_path = os.path.join(tmp_path, store.ATTRS_FILENAME_COLLECTIONS)
    datasets_metadata_path = os.path.join(tmp_path, store.ATTRS_FILENAME_DATASETS)
    with open(collections_metadata_path) as f:
        hdcas_metadata = json.load(f)

    assert len(hdcas_metadata) == 1
    hdca_metadata = hdcas_metadata[0]
    assert hdca_metadata
    assert "id" in hdca_metadata
    assert "collection" in hdca_metadata
    collection_metadata = hdca_metadata["collection"]
    assert "populated_state" in collection_metadata
    assert collection_metadata["populated_state"] == model.DatasetCollection.populated_states.NEW

    collection_metadata["populated_state"] = model.DatasetCollection.populated_states.OK

    d1 = model.HistoryDatasetAssociation(extension="txt", create_dataset=True, flush=False)
    d1.hid = 1
    d2 = model.HistoryDatasetAssociation(extension="txt", create_dataset=True, flush=False)
    d2.hid = 2
    serialization_options = model.SerializationOptions(for_edit=True)
    dataset_list = [
        d1.serialize(app.security, serialization_options),
        d2.serialize(app.security, serialization_options),
    ]

    dc = model.DatasetCollection(
        id=collection_metadata["id"],
        collection_type="list",
        element_count=2,
    )
    dc.populated_state = model.DatasetCollection.populated_states.OK
    dce1 = model.DatasetCollectionElement(
        element=d1,
        element_index=0,
        element_identifier="first",
    )
    dce2 = model.DatasetCollectionElement(
        element=d2,
        element_index=1,
        element_identifier="second",
    )
    dc.elements = [dce1, dce2]
    with open(datasets_metadata_path, "w") as datasets_f:
        json.dump(dataset_list, datasets_f)

    hdca_metadata["collection"] = dc.serialize(app.security, serialization_options)
    with open(collections_metadata_path, "w") as collections_f:
        json.dump(hdcas_metadata, collections_f)

    _perform_import_from_directory(tmp_path, app, u, import_history, store.ImportOptions(allow_edit=True))

    sa_session.refresh(c1)
    assert c1.populated_state == model.DatasetCollection.populated_states.OK, c1.populated_state
    assert len(c1.elements) == 2


def test_import_export_composite_datasets(tmp_path):
    app = _mock_app()
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1 = _create_datasets(sa_session, h, 1, extension="html")[0]
    d1.dataset.create_extra_files_path()
    app.add_and_commit(h, d1)

    app.write_primary_file(d1, "cool primary file")
    app.write_composite_file(d1, "cool composite file", "child_file")

    with store.DirectoryModelExportStore(tmp_path, app=app, export_files="copy") as export_store:
        export_store.add_dataset(d1)

    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)
    _perform_import_from_directory(tmp_path, app, u, import_history)
    assert len(import_history.datasets) == 1
    import_dataset = import_history.datasets[0]
    _assert_extra_files_has_parent_directory_with_single_file_containing(
        import_dataset, "child_file", "cool composite file"
    )


def _assert_extra_files_has_parent_directory_with_single_file_containing(
    dataset, expected_file_name, expected_contents
):
    root_extra_files_path = dataset.extra_files_path
    assert len(os.listdir(root_extra_files_path)) == 1
    assert os.listdir(root_extra_files_path)[0] == "parent_dir"
    composite_sub_dir = os.path.join(root_extra_files_path, "parent_dir")
    child_files = os.listdir(composite_sub_dir)
    assert len(child_files) == 1
    assert child_files[0] == expected_file_name
    with open(os.path.join(composite_sub_dir, child_files[0])) as f:
        contents = f.read()
        assert contents == expected_contents


def test_edit_metadata_files(tmp_path):
    app = _mock_app(store_by="uuid")
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1 = _create_datasets(sa_session, h, 1, extension="bam")[0]
    app.add_and_commit(h, d1)
    index = NamedTemporaryFile("w")
    index.write("cool bam index")
    metadata_dict = {"bam_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": index.name})}
    d1.metadata.from_JSON_dict(json_dict=metadata_dict)
    assert d1.metadata.bam_index
    assert isinstance(d1.metadata.bam_index, model.MetadataFile)

    with store.DirectoryModelExportStore(tmp_path, app=app, for_edit=True, strip_metadata_files=False) as export_store:
        export_store.add_dataset(d1)

    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)
    _perform_import_from_directory(tmp_path, app, u, import_history, store.ImportOptions(allow_edit=True))


def test_sessionless_import_edit_datasets():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    # Create a model store without a session and import it.
    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, import_options=store.ImportOptions(allow_dataset_object_edit=True, allow_edit=True)
    )
    import_model_store.perform_import()
    # Not using app.sa_session but a session mock that has a query/find pattern emulating usage
    # of real sa_session.
    assert isinstance(import_model_store.sa_session, SessionlessContext)
    d1 = import_model_store.sa_session.query(model.HistoryDatasetAssociation).find(h.datasets[0].id)
    d2 = import_model_store.sa_session.query(model.HistoryDatasetAssociation).find(h.datasets[1].id)
    assert d1 is not None
    assert d2 is not None


def test_import_job_with_output_copy():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    hda = h.active_datasets[-1]
    # Simulate a copy being made of an output hda
    copy = hda.copy(new_name="output copy")
    # set extension to auto, should be changed to real extension when finalizing job
    copy.extension = "auto"
    app.add_and_commit(copy)
    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, import_options=store.ImportOptions(allow_dataset_object_edit=True, allow_edit=True), app=app
    )
    import_model_store.perform_import()
    assert copy.extension == "txt"


def test_import_existing_job_reports_state_without_applying_it():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    job = h.active_datasets[-1].creating_job
    assert job
    job.state = model.Job.states.RUNNING
    app.commit()
    import_model_store = store.get_import_model_store_for_directory(
        temp_directory, import_options=store.ImportOptions(allow_dataset_object_edit=True, allow_edit=True), app=app
    )
    object_import_tracker = import_model_store.perform_import()
    assert job.state == model.Job.states.RUNNING
    assert app.model.session.scalar(select(model.Job.state).where(model.Job.id == job.id)) == model.Job.states.RUNNING
    assert object_import_tracker.job_states_by_id == {job.id: model.Job.states.OK}


def test_import_datasets_with_ids_fails_if_not_editing_models():
    app, h, temp_directory, import_history = _setup_simple_export({"for_edit": True})
    u = h.user

    caught = None
    try:
        _perform_import_from_directory(temp_directory, app, u, import_history, store.ImportOptions(allow_edit=False))
    except AssertionError as e:
        # TODO: catch a better exception
        caught = e
    assert caught


def _setup_simple_export(export_kwds):
    app = _mock_app()

    u, h, d1, d2, j = _setup_simple_cat_job(app)

    import_history = model.History(name="Test History for Import", user=u)
    app.add_and_commit(import_history)

    temp_directory = mkdtemp()
    with store.DirectoryModelExportStore(temp_directory, app=app, **export_kwds) as export_store:
        export_store.add_dataset(d1)
        export_store.add_dataset(d2)

    return app, h, temp_directory, import_history


def _assert_simple_cat_job_imported(imported_history, state="ok"):
    assert imported_history.name == "imported from archive: Test History"

    datasets = imported_history.datasets
    assert len(datasets) == 2
    assert datasets[0].state == datasets[1].state == state
    imported_job = datasets[1].creating_job
    assert imported_job
    assert imported_job.state == state
    assert imported_job.output_datasets
    assert imported_job.output_datasets[0].dataset == datasets[1]

    assert imported_job.input_datasets
    assert imported_job.input_datasets[0].dataset == datasets[0]

    with open(datasets[0].get_file_name()) as f:
        assert f.read().startswith("chr1    4225    19670")
    with open(datasets[1].get_file_name()) as f:
        assert f.read().startswith("chr1\t147962192\t147962580\tNM_005997_cds_0_0_chr1_147962193_r\t0\t-")


def _setup_simple_cat_job(app, state="ok"):
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1, d2 = _create_datasets(sa_session, h, 2)
    d1.state = d2.state = state

    j = model.Job()
    j.user = u
    j.tool_id = "cat1"
    j.state = state

    j.add_input_dataset("input1", d1)
    j.add_output_dataset("out_file1", d2)

    app.add_and_commit(d1, d2, h, j)
    j.input_datasets[0].dataset_version = d1.version
    app.commit()

    app.object_store.update_from_file(d1, file_name=TEST_PATH_1, create=True)
    app.object_store.update_from_file(d2, file_name=TEST_PATH_2, create=True)

    return u, h, d1, d2, j


def _setup_invocation(app):
    sa_session = app.model.context

    # Set up a user, history, datasets, and job
    u, h, d1, d2, j = _setup_simple_cat_job(app)
    j.tool_id = "example_tool"
    j.tool_version = "1.0"
    j.parameters = [model.JobParameter(name="index_path", value='"/old/path/human"')]

    # Create a workflow
    workflow = model.Workflow()
    workflow.license = "MIT"
    workflow.name = "Test Workflow"
    workflow.creator_metadata = [
        {"class": "Person", "name": "Alice", "identifier": "0000-0001-2345-6789", "email": "alice@example.com"},
    ]

    # Create and associate a data_input step
    workflow_step_1 = model.WorkflowStep()
    workflow_step_1.order_index = 0
    workflow_step_1.type = "data_input"
    workflow_step_1.label = "Input Step"
    workflow.steps.append(workflow_step_1)
    sa_session.add(workflow_step_1)  # Persist step in the session

    # Create and associate a tool step
    workflow_step_2 = model.WorkflowStep()
    workflow_step_2.order_index = 0
    workflow_step_2.type = "tool"
    workflow_step_2.tool_id = "example_tool"
    workflow_step_2.tool_version = "1.0"
    workflow_step_2.label = "Example Tool Step"
    workflow.steps.append(workflow_step_2)
    sa_session.add(workflow_step_2)  # Persist step in the session

    sa_session.add(workflow)  # Persist the workflow itself

    # Create a workflow invocation
    workflow_invocation = _invocation_for_workflow(u, workflow)

    # Associate invocation step for data_input
    invocation_step_1 = model.WorkflowInvocationStep()
    invocation_step_1.workflow_step = workflow_step_1
    sa_session.add(invocation_step_1)

    # Associate invocation step for tool
    invocation_step_2 = model.WorkflowInvocationStep()
    invocation_step_2.workflow_step = workflow_step_2
    invocation_step_2.job = j
    sa_session.add(invocation_step_2)

    # Add steps to the invocation
    workflow_invocation.steps = [invocation_step_1, invocation_step_2]
    workflow_invocation.user = u
    workflow_invocation.add_input(d1, step=workflow_step_1)

    # Add workflow output associated with the tool step
    wf_output = model.WorkflowOutput(workflow_step_2, label="output_label")
    workflow_invocation.add_output(wf_output, workflow_step_2, d2)

    # Commit the workflow and invocation
    app.add_and_commit(workflow_invocation)

    return workflow_invocation


def _setup_simple_collection_job(app, state="ok"):
    sa_session = app.model.context

    u = model.User(email="collection@example.com", password="password")
    h = model.History(name="Test History", user=u)

    d1, d2, d3, d4 = _create_datasets(sa_session, h, 4)

    c1 = model.DatasetCollection(collection_type="list")
    hc1 = model.HistoryDatasetCollectionAssociation(history=h, hid=1, collection=c1, name="HistoryCollectionTest1")
    dce1 = model.DatasetCollectionElement(collection=c1, element=d1, element_identifier="forward", element_index=0)
    dce2 = model.DatasetCollectionElement(collection=c1, element=d2, element_identifier="reverse", element_index=1)

    c2 = model.DatasetCollection(collection_type="list")
    hc2 = model.HistoryDatasetCollectionAssociation(history=h, hid=2, collection=c2, name="HistoryCollectionTest2")
    dce3 = model.DatasetCollectionElement(collection=c2, element=d1, element_identifier="forward", element_index=0)
    dce4 = model.DatasetCollectionElement(collection=c2, element=d3, element_identifier="reverse", element_index=1)

    c3 = model.DatasetCollection(collection_type="list")
    hc3 = model.HistoryDatasetCollectionAssociation(history=h, hid=3, collection=c3, name="HistoryCollectionTest3")
    dce5 = model.DatasetCollectionElement(collection=c3, element=d4, element_identifier="out", element_index=0)

    j = model.Job()
    j.user = h.user
    j.tool_id = "cat1"
    j.add_input_dataset("input1", d1)
    j.add_input_dataset("input2", d2)
    j.add_input_dataset("input3", d3)
    j.add_output_dataset("out_file1", d4)
    j.add_input_dataset_collection("input1_collect", hc1)
    j.add_input_dataset_collection("input2_collect", hc2)
    j.add_output_dataset_collection("output", hc3)

    sa_session.add(dce1)
    sa_session.add(dce2)
    sa_session.add(dce3)
    sa_session.add(dce4)
    sa_session.add(dce5)
    sa_session.add(hc1)
    sa_session.add(hc2)
    sa_session.add(hc3)
    sa_session.add(j)
    app.commit()

    return u, h, c1, c2, c3, hc1, hc2, hc3, j


def _setup_collection_invocation(app):
    sa_session = app.model.context

    u, h, c1, c2, c3, hc1, hc2, hc3, j = _setup_simple_collection_job(app)

    workflow_step_1 = model.WorkflowStep()
    workflow_step_1.order_index = 0
    workflow_step_1.type = "data_collection_input"
    workflow_step_1.tool_inputs = {}
    sa_session.add(workflow_step_1)
    workflow_step_2 = model.WorkflowStep()
    workflow_step_2.order_index = 1
    workflow_step_2.type = "data_collection_input"
    workflow_step_2.tool_inputs = {}
    sa_session.add(workflow_step_2)
    workflow_1 = _workflow_from_steps(u, [workflow_step_1, workflow_step_2])
    workflow_1.license = "MIT"
    workflow_1.name = "Test Workflow"
    sa_session.add(workflow_1)
    workflow_invocation = _invocation_for_workflow(u, workflow_1)
    workflow_invocation.user = u
    workflow_invocation.add_input(hc1, step=workflow_step_1)
    workflow_invocation.add_input(hc2, step=workflow_step_2)
    wf_output = model.WorkflowOutput(workflow_step_1, label="output_label")
    workflow_invocation.add_output(wf_output, workflow_step_1, hc3)

    app.add_and_commit(workflow_invocation)
    return workflow_invocation


def _setup_simple_invocation(app):
    sa_session = app.model.context

    # Set up a simple user, history, datasets, and job
    u, h, d1, d2, j = _setup_simple_cat_job(app)
    j.parameters = [model.JobParameter(name="index_path", value='"/old/path/human"')]

    # Create a workflow
    workflow_step_1 = model.WorkflowStep()
    workflow_step_1.order_index = 0
    workflow_step_1.type = "data_input"
    workflow_step_1.tool_inputs = {}
    sa_session.add(workflow_step_1)
    workflow = _workflow_from_steps(u, [workflow_step_1])
    workflow.license = "MIT"
    workflow.name = "Test Workflow"
    workflow.creator_metadata = [
        {"class": "Person", "name": "Bob", "identifier": "0000-0002-3456-7890", "email": "bob@example.com"},
    ]

    # Create and associate a tool step
    workflow_step_tool = model.WorkflowStep()
    workflow_step_tool.order_index = 1
    workflow_step_tool.type = "tool"
    workflow_step_tool.tool_id = "example_tool"
    workflow_step_tool.tool_version = "1.0"
    workflow_step_tool.label = "Example Tool Step"
    workflow.steps.append(workflow_step_tool)

    sa_session.add(workflow)

    # Create a workflow invocation
    invocation = _invocation_for_workflow(u, workflow)
    invocation.add_input(d1, step=workflow_step_1)  # Associate input dataset
    wf_output = model.WorkflowOutput(workflow_step_tool, label="output_label")
    invocation.add_output(wf_output, workflow_step_tool, d2)  # Associate output dataset

    # Commit the workflow and invocation to the database
    app.add_and_commit(invocation)

    return invocation


def _import_export_history(app, h, dest_export=None, export_files=None, import_options=None, include_hidden=False):
    if dest_export is None:
        dest_parent = mkdtemp()
        dest_export = os.path.join(dest_parent, "moo.tgz")

    with store.TarModelExportStore(dest_export, app=app, export_files=export_files) as export_store:
        export_store.export_history(h, include_hidden=include_hidden)

    imported_history = import_archive(dest_export, app, h.user, import_options=import_options)
    assert imported_history
    return imported_history


def _perform_import_from_directory(directory, app, user, import_history, import_options=None):
    import_model_store = store.get_import_model_store_for_directory(
        directory, app=app, user=user, import_options=import_options
    )
    with import_model_store.target_history(default_history=import_history):
        import_model_store.perform_import(import_history)


def _create_datasets(sa_session, history, n, extension="txt"):
    return [
        model.HistoryDatasetAssociation(
            extension=extension, history=history, create_dataset=True, sa_session=sa_session, hid=i + 1
        )
        for i in range(n)
    ]


class MockWorkflowContentsManager:
    def store_workflow_artifacts(self, directory, workflow_key, workflow, **kwd):
        path = os.path.join(directory, f"{workflow_key}.gxwf.yml")
        with open(path, "w") as f:
            f.write("MY COOL WORKFLOW!!!")
        path = os.path.join(directory, f"{workflow_key}.abstract.cwl")
        with open(path, "w") as f:
            f.write("MY COOL WORKFLOW as CWL!!!")

    def read_workflow_from_path(self, app, user, path, allow_in_directory=None):
        stored_workflow = model.StoredWorkflow()
        stored_workflow.user = user
        workflow_step_1 = model.WorkflowStep()
        workflow_step_1.order_index = 0
        workflow_step_1.type = "data_input"
        workflow = model.Workflow()
        workflow.steps = [workflow_step_1]
        stored_workflow.latest_workflow = workflow
        app.add_and_commit(stored_workflow, workflow)
        return workflow


class TestApp(GalaxyDataTestApp):
    workflow_contents_manager = MockWorkflowContentsManager()

    def add_and_commit(self, *objs):
        session = self.model.session
        session.add_all(objs)
        self.commit()

    def commit(self):
        session = self.model.session
        session.commit()

    def write_primary_file(self, dataset_instance, contents):
        primary = NamedTemporaryFile("w")
        primary.write(contents)
        primary.flush()
        self.object_store.update_from_file(
            dataset_instance.dataset, file_name=primary.name, create=True, preserve_symlinks=True
        )

    def write_composite_file(self, dataset_instance, contents, file_name):
        composite1 = NamedTemporaryFile("w")
        composite1.write(contents)
        composite1.flush()

        dataset_instance.dataset.create_extra_files_path()
        self.object_store.update_from_file(
            dataset_instance.dataset,
            extra_dir=os.path.normpath(os.path.join(dataset_instance.extra_files_path, "parent_dir")),
            alt_name=file_name,
            file_name=composite1.name,
            create=True,
            preserve_symlinks=True,
        )


def _mock_app(store_by=DEFAULT_OBJECT_STORE_BY):
    app = TestApp()
    test_object_store_config = TestConfig(store_by=store_by)
    app.object_store = test_object_store_config.object_store
    model.Dataset.object_store = app.object_store

    return app


class StoreFixtureContextWithUser(NamedTuple):
    app: TestApp
    sa_session: scoped_session
    user: model.User


def setup_fixture_context_with_user(
    user_email="test@example.com", store_by=DEFAULT_OBJECT_STORE_BY
) -> StoreFixtureContextWithUser:
    app = _mock_app(store_by=store_by)
    sa_session = app.model.context
    user = model.User(email=user_email, password="password")
    return StoreFixtureContextWithUser(app=app, sa_session=sa_session, user=user)


class StoreFixtureContextWithHistory(NamedTuple):
    app: TestApp
    sa_session: scoped_session
    user: model.User
    history: model.History


def setup_fixture_context_with_history(
    history_name="Test History for Model Store", **kwd
) -> StoreFixtureContextWithHistory:
    app, sa_session, user = setup_fixture_context_with_user(**kwd)
    history = model.History(name=history_name, user=user)
    sa_session.add(history)
    app.commit()
    return StoreFixtureContextWithHistory(app, sa_session, user, history)


def perform_import_from_store_dict(
    fixture_context: StoreFixtureContextWithHistory,
    import_dict: dict[str, Any],
    import_options: store.ImportOptions | None = None,
) -> None:
    import_options = import_options or store.ImportOptions()
    import_model_store = store.get_import_model_store_for_dict(
        import_dict, app=fixture_context.app, user=fixture_context.user, import_options=import_options
    )
    with import_model_store.target_history(default_history=fixture_context.history):
        import_model_store.perform_import(fixture_context.history)


class Options:
    is_url = False
    is_file = True
    is_b64encoded = False


def import_archive(archive_path, app, user, import_options=None):
    dest_parent = mkdtemp()
    with CompressedFile(archive_path) as cf:
        dest_dir = cf.extract(dest_parent)

    import_options = import_options or store.ImportOptions()
    model_store = store.get_import_model_store_for_directory(
        dest_dir,
        app=app,
        user=user,
        import_options=import_options,
    )
    with model_store.target_history(default_history=None) as new_history:
        model_store.perform_import(new_history)

    shutil.rmtree(dest_parent)

    return new_history
