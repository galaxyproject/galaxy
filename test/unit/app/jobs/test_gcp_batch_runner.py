"""Unit tests for Google Cloud Batch job runner utility methods."""

from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.jobs.runners import RunnerParams
from galaxy.jobs.runners.gcp_batch import (
    GoogleCloudBatchJobRunner,
    RUNNER_PARAM_SPECS,
)
from galaxy.jobs.runners.util.gcp_batch import (
    compute_gpu_machine_type,
    convert_cpu_to_milli,
    convert_duration_to_seconds,
    convert_memory_to_mib,
    DEFAULT_MAX_RUN_DURATION,
    parse_docker_volumes_param,
    parse_volume_spec,
    parse_volumes_param,
    resolve_gpu_count,
    resolve_max_run_duration,
    sanitize_label_value,
)


class TestSanitizeLabelValue:
    """Tests for sanitize_label_value helper function."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("HelloWorld", "helloworld"),  # lowercase conversion
            ("tool@1.0", "tool-1-0"),  # invalid chars replaced
            ("a--b---c", "a-b-c"),  # consecutive dashes collapsed
            ("--value--", "value"),  # leading/trailing dashes stripped
            ("", "unknown"),  # empty string
            (None, "unknown"),  # None value
            ("@#$%", "unknown"),  # all invalid chars
            ("valid-label_123", "valid-label-123"),  # underscores replaced with dashes
            ("a" * 100, "a" * 63),  # truncation at max_length
            ("a" * 62 + "-x", "a" * 62),  # a truncated identified does not end with a dash
        ],
    )
    def test_sanitize_label_value(self, input_value, expected):
        result = sanitize_label_value(input_value)
        assert result == expected


class TestConvertCpuToMilli:
    """Tests for convert_cpu_to_milli helper function."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("2", 2000),  # integer string
            ("1.5", 1500),  # decimal string
            ("500m", 500),  # milli format
            ("0.25", 250),  # fractional cpu
            ("", 1000),  # empty string -> default
            (None, 1000),  # None -> default
            ("abcm", 1000),  # invalid milli format -> default
            ("invalid", 1000),  # invalid format -> default
            ("1", 1000),  # single cpu
            ("4", 4000),  # four cpus
            ("100m", 100),  # small milli value
            ("2500m", 2500),  # larger milli value
        ],
    )
    def test_convert_cpu_to_milli(self, input_value, expected):
        result = convert_cpu_to_milli(input_value)
        assert result == expected


class TestConvertMemoryToMib:
    """Tests for convert_memory_to_mib helper function."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("2048", 2048),  # plain number
            ("512Mi", 512),  # MiB suffix
            ("512MiB", 512),  # MiB suffix (full)
            ("2Gi", 2048),  # GiB suffix
            ("1gib", 1024),  # GiB lowercase
            ("1024", 1024),  # plain number
            ("", 2048),  # empty -> default
            (None, 2048),  # None -> default
            ("invalid-format", 2048),  # invalid -> default
            ("1.5Gi", 1536),  # decimal GiB
            ("256Mi", 256),  # small MiB value
            ("4Gi", 4096),  # larger GiB value
            # Decimal units (KB/MB/GB use powers of 1000, converted to MiB)
            ("1gb", 953),  # 1 GB -> MiB (10^9 / 1024^2)
            ("4gb", 3814),  # larger GB value
            ("2g", 1907),  # GB short form
            ("1000mb", 953),  # 1000 MB == 1 GB == 953 MiB (consistency check)
            ("1024mb", 976),  # MB -> MiB
            ("1000m", 953),  # MB short form
            ("1048576kb", 1000),  # KB -> MiB
            # Binary KiB
            ("1024kib", 1),  # KiB -> MiB (value / 1024)
            ("2048ki", 2),  # KiB short form
            # Unknown unit falls back to treating the value as MiB
            ("5xyz", 5),
        ],
    )
    def test_convert_memory_to_mib(self, input_value, expected):
        result = convert_memory_to_mib(input_value)
        assert result == expected


class TestParseVolumeSpec:
    """Tests for parse_volume_spec helper function."""

    def test_basic_nfs_volume(self):
        result = parse_volume_spec("10.0.0.1:/galaxy:/mnt/nfs")
        assert result == {
            "server": "10.0.0.1",
            "remote_path": "/galaxy",
            "mount_path": "/mnt/nfs",
            "read_only": False,
        }

    def test_read_only_volume(self):
        result = parse_volume_spec("nfs-server:/exports:/data:ro")
        assert result == {
            "server": "nfs-server",
            "remote_path": "/exports",
            "mount_path": "/data",
            "read_only": True,
        }

    def test_read_only_with_r(self):
        result = parse_volume_spec("server:/path:/mount:r")
        assert result is not None
        assert result["read_only"] is True

    def test_read_only_with_readonly(self):
        result = parse_volume_spec("server:/path:/mount:readonly")
        assert result is not None
        assert result["read_only"] is True

    def test_invalid_too_few_parts(self):
        result = parse_volume_spec("server:/path")
        assert result is None

    def test_empty_string(self):
        result = parse_volume_spec("")
        assert result is None

    def test_none_input(self):
        result = parse_volume_spec(None)
        assert result is None

    def test_whitespace_handling(self):
        result = parse_volume_spec(" server : /path : /mount ")
        assert result == {
            "server": "server",
            "remote_path": "/path",
            "mount_path": "/mount",
            "read_only": False,
        }


class TestParseVolumesParam:
    """Tests for parse_volumes_param helper function."""

    def test_single_volume(self):
        result = parse_volumes_param("10.0.0.1:/galaxy:/mnt/nfs")
        assert len(result) == 1
        assert result[0]["server"] == "10.0.0.1"

    def test_multiple_volumes(self):
        result = parse_volumes_param("10.0.0.1:/galaxy:/mnt/nfs,cvmfs:/cvmfs:/cvmfs:ro")
        assert len(result) == 2
        assert result[0]["server"] == "10.0.0.1"
        assert result[0]["read_only"] is False
        assert result[1]["server"] == "cvmfs"
        assert result[1]["read_only"] is True

    def test_empty_string(self):
        result = parse_volumes_param("")
        assert result == []

    def test_none_input(self):
        result = parse_volumes_param(None)
        assert result == []

    def test_whitespace_between_volumes(self):
        result = parse_volumes_param("server1:/p1:/m1 , server2:/p2:/m2")
        assert len(result) == 2

    def test_invalid_volumes_skipped(self):
        result = parse_volumes_param("valid:/path:/mount,invalid,another:/p:/m")
        assert len(result) == 2


class TestParseDockerVolumesParam:
    """Tests for parse_docker_volumes_param helper function."""

    def test_single_volume(self):
        result = parse_docker_volumes_param("/host/path:/container/path")
        assert result == '-v "/host/path:/container/path"'

    def test_multiple_volumes(self):
        result = parse_docker_volumes_param("/path1:/mount1,/path2:/mount2:ro")
        assert result == '-v "/path1:/mount1" -v "/path2:/mount2:ro"'

    def test_empty_string(self):
        result = parse_docker_volumes_param("")
        assert result == ""

    def test_none_input(self):
        result = parse_docker_volumes_param(None)
        assert result == ""

    def test_cvmfs_example(self):
        result = parse_docker_volumes_param("/cvmfs/data.galaxyproject.org:/cvmfs/data.galaxyproject.org:ro")
        assert result == '-v "/cvmfs/data.galaxyproject.org:/cvmfs/data.galaxyproject.org:ro"'


class TestConvertDurationToSeconds:
    """Tests for convert_duration_to_seconds helper function."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("3600s", "3600s"),  # seconds suffix
            ("86400s", "86400s"),  # larger seconds value
            ("0s", "0s"),  # zero seconds
            ("30m", "1800s"),  # minutes to seconds
            ("90m", "5400s"),  # larger minutes
            ("2h", "7200s"),  # hours to seconds
            ("24h", "86400s"),  # 24 hours
            ("1d", "86400s"),  # days to seconds
            ("7d", "604800s"),  # 7 days
            ("3600", "3600s"),  # plain integer string (seconds assumed)
            ("86400", "86400s"),  # plain integer string
            (3600, "3600s"),  # numeric int
            (7200, "7200s"),  # numeric int
            (7200.0, "7200s"),  # numeric float
            ("1.5h", "5400s"),  # fractional hours
            ("2.5d", "216000s"),  # fractional days
            ("0.5h", "1800s"),  # half hour
            ("", DEFAULT_MAX_RUN_DURATION),  # empty string -> default
            (None, DEFAULT_MAX_RUN_DURATION),  # None -> default
            ("invalid", DEFAULT_MAX_RUN_DURATION),  # garbage -> default
            ("abcs", DEFAULT_MAX_RUN_DURATION),  # invalid with s suffix -> default
            ("xxh", DEFAULT_MAX_RUN_DURATION),  # invalid with h suffix -> default
            ("zzm", DEFAULT_MAX_RUN_DURATION),  # invalid with m suffix -> default
            ("qqd", DEFAULT_MAX_RUN_DURATION),  # invalid with d suffix -> default
        ],
    )
    def test_convert_duration_to_seconds(self, input_value, expected):
        result = convert_duration_to_seconds(input_value)
        assert result == expected


class TestResolveMaxRunDuration:
    """Tests for resolve_max_run_duration priority resolution."""

    def test_resource_param_walltime_highest_priority(self):
        """User-specified walltime wins over everything."""
        result = resolve_max_run_duration(
            destination_params={"max_run_duration": "2h"},
            runner_params={"max_run_duration": "1h"},
            resource_params={"walltime": "3600"},
        )
        assert result == "3600s"

    def test_destination_max_run_duration_over_dest_walltime(self):
        """Destination 'max_run_duration' beats destination 'walltime'."""
        result = resolve_max_run_duration(
            destination_params={"max_run_duration": "2h", "walltime": "1h"},
            runner_params={"max_run_duration": "86400s"},
            resource_params={},
        )
        assert result == "7200s"

    def test_destination_walltime_over_runner_default(self):
        """Destination 'walltime' beats the runner-level default."""
        result = resolve_max_run_duration(
            destination_params={"walltime": "4h"},
            runner_params={"max_run_duration": "86400s"},
            resource_params={},
        )
        assert result == "14400s"

    def test_runner_default_fallback(self):
        """Falls back to runner-level max_run_duration when nothing else set."""
        result = resolve_max_run_duration(
            destination_params={},
            runner_params={"max_run_duration": "3600s"},
            resource_params={},
        )
        assert result == "3600s"

    def test_global_default_when_nothing_set(self):
        """Falls back to DEFAULT_MAX_RUN_DURATION when params dict has no key."""
        result = resolve_max_run_duration(
            destination_params={},
            runner_params={},
            resource_params={},
        )
        assert result == DEFAULT_MAX_RUN_DURATION

    def test_resource_walltime_over_destination_max_run_duration(self):
        """User walltime overrides destination max_run_duration."""
        result = resolve_max_run_duration(
            destination_params={"max_run_duration": "1h"},
            runner_params={"max_run_duration": "86400s"},
            resource_params={"walltime": "2d"},
        )
        assert result == "172800s"

    def test_destination_max_run_duration_normalizes_format(self):
        """Duration values are normalized through convert_duration_to_seconds."""
        result = resolve_max_run_duration(
            destination_params={"max_run_duration": "48h"},
            runner_params={},
            resource_params={},
        )
        assert result == "172800s"

    def test_empty_walltime_ignored(self):
        """Empty walltime in resource params is skipped."""
        result = resolve_max_run_duration(
            destination_params={},
            runner_params={"max_run_duration": "7200s"},
            resource_params={"walltime": ""},
        )
        assert result == "7200s"


def _sleep_runner(runner_params, job_runner_monitor_sleep=1.0):
    """A runner instance with __init__ skipped, for exercising monitor_sleep_time."""
    runner = object.__new__(GoogleCloudBatchJobRunner)
    runner.runner_params = runner_params
    config = SimpleNamespace(job_runner_monitor_sleep=job_runner_monitor_sleep)
    runner.app = cast(Any, SimpleNamespace(config=config))
    return runner


class TestMonitorSleepTime:
    """The runner throttles its monitor loop to the configured polling_interval so
    the base loop does not poll the GCP Batch API more often than necessary."""

    def test_uses_polling_interval_over_default_monitor_sleep(self):
        runner = _sleep_runner({"polling_interval": 30}, job_runner_monitor_sleep=1.0)
        assert runner.monitor_sleep_time == 30

    def test_respects_larger_monitor_sleep(self):
        # max(global, polling_interval): a larger global sleep wins.
        runner = _sleep_runner({"polling_interval": 30}, job_runner_monitor_sleep=60)
        assert runner.monitor_sleep_time == 60

    def test_interval_default_resolves_via_spec(self):
        # polling_interval unset -> must fall back to the spec default (30) through
        # ParamsWithSpecs.__missing__; .get() would yield None and raise in max().
        runner = _sleep_runner(RunnerParams(specs={"polling_interval": dict(map=int, default=30)}, params={}))
        assert runner.monitor_sleep_time == 30


def _make_runner(runner_params=None):
    """Build a GoogleCloudBatchJobRunner without running __init__ (no GCP client).

    _get_job_params only depends on self.runner_params, so we set that directly.
    """
    runner = object.__new__(GoogleCloudBatchJobRunner)
    runner.runner_params = RunnerParams(specs=RUNNER_PARAM_SPECS, params=runner_params or {})
    return runner


# Keys that _get_job_params copies from the destination / runner config. Derived
# dynamically (rather than hard-coded) so the parametrized tests below automatically
# cover any parameter added to _get_job_params in the future.
JOB_PARAM_KEYS = sorted(_make_runner()._get_job_params(SimpleNamespace(params={})).keys())


class TestGetJobParams:
    """Tests for GoogleCloudBatchJobRunner._get_job_params default resolution."""

    @pytest.mark.parametrize("key", JOB_PARAM_KEYS)
    def test_unset_param_falls_back_to_spec_default(self, key):
        """Every copied parameter resolves to its spec default when nothing overrides it.

        This is the regression guard: .get() on the RunnerParams defaultdict would
        bypass __missing__ and yield None instead of the configured default.
        """
        runner = _make_runner()
        destination = SimpleNamespace(params={})

        params = runner._get_job_params(destination)

        assert params[key] == RUNNER_PARAM_SPECS[key]["default"]

    @pytest.mark.parametrize("key", JOB_PARAM_KEYS)
    def test_destination_overrides_every_param(self, key):
        """A value on the job destination takes precedence over the spec default for every param.

        Destination params are not passed through the RunnerParams spec mapping, so a
        plain string sentinel is a valid override for every key.
        """
        runner = _make_runner()
        sentinel = "destination-sentinel-value"
        destination = SimpleNamespace(params={key: sentinel})

        params = runner._get_job_params(destination)

        assert params[key] == sentinel

    def test_runner_config_overrides_default(self):
        """A value set in the runner (plugin) config is used when the destination is silent."""
        runner = _make_runner({"job_id_prefix": "from-config"})
        destination = SimpleNamespace(params={})

        params = runner._get_job_params(destination)

        assert params["job_id_prefix"] == "from-config"

    def test_destination_overrides_runner_config(self):
        """Destination params win over runner config, which wins over the spec default."""
        runner = _make_runner({"job_id_prefix": "from-config"})
        destination = SimpleNamespace(params={"job_id_prefix": "from-destination"})

        params = runner._get_job_params(destination)

        assert params["job_id_prefix"] == "from-destination"


class TestComputeGpuMachineType:
    """L4 GPU jobs select the smallest g2-standard shape satisfying gpus/cores/mem."""

    @pytest.mark.parametrize(
        "gpu_count,cpu_milli,memory_mib,expected",
        [
            (1, 32000, 116 * 1024, "g2-standard-32"),  # the image_learner example
            (1, 1000, 1024, "g2-standard-4"),  # smallest single-GPU shape
            (1, 8000, 30 * 1024, "g2-standard-8"),
            (1, 12000, 40 * 1024, "g2-standard-12"),
            (1, 16000, 64 * 1024, "g2-standard-16"),  # exact fit
            (1, 1000, 100 * 1024, "g2-standard-32"),  # memory-driven, not cpu-driven
            (2, 24000, 96 * 1024, "g2-standard-24"),
            (4, 48000, 192 * 1024, "g2-standard-48"),
            (8, 96000, 384 * 1024, "g2-standard-96"),
        ],
    )
    def test_selects_expected_machine_type(self, gpu_count, cpu_milli, memory_mib, expected):
        assert compute_gpu_machine_type(gpu_count, cpu_milli, memory_mib) == expected

    @pytest.mark.parametrize("gpu_count", [3, 5, 6, 7, 16])
    def test_unsupported_gpu_count_raises(self, gpu_count):
        with pytest.raises(ValueError, match="not supported"):
            compute_gpu_machine_type(gpu_count, 4000, 16 * 1024)

    @pytest.mark.parametrize(
        "gpu_count,cpu_milli,memory_mib",
        [
            (1, 64000, 16 * 1024),  # 64 vCPU exceeds the largest single-L4 shape (32)
            (1, 1000, 200 * 1024),  # 200 GiB exceeds the largest single-L4 shape (128)
            (2, 32000, 96 * 1024),  # 2 L4 only on g2-standard-24 (24 vCPU) < 32
        ],
    )
    def test_oversize_request_raises(self, gpu_count, cpu_milli, memory_mib):
        with pytest.raises(ValueError, match="satisfies the requested"):
            compute_gpu_machine_type(gpu_count, cpu_milli, memory_mib)


class TestResolveGpuCount:
    """gpus is a TPV scheduling quantity: a string, possibly fractional, that has to
    become a whole number of physical L4 devices."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, 0),  # unset
            ("", 0),  # empty destination interpolation
            (0, 0),
            ("0", 0),  # every non-GPU job arrives here once the destination forwards gpus
            ("0.0", 0),
            (1, 1),
            ("1", 1),  # the common case: forwarded as a string
            ("2", 2),
            ("8", 8),
            (0.25, 1),  # a share of a GPU still needs a whole card (upstream libcarna_render)
            ("0.25", 1),
            ("0.5", 1),
            ("1.5", 2),  # rounds up, never down
            (1.0, 1),
            ("1.0", 1),
        ],
    )
    def test_resolves_to_whole_gpus(self, value, expected):
        assert resolve_gpu_count(value) == expected

    @pytest.mark.parametrize("value", ["abc", "1x", "{gpus}", object(), "nan", "inf"])
    def test_non_numeric_raises_with_a_useful_message(self, value):
        with pytest.raises(ValueError, match="Invalid GPU request"):
            resolve_gpu_count(value)

    @pytest.mark.parametrize("value,expected", [("1", 1), ("0.25", 1), (0, 0)])
    def test_runner_config_values_go_through_the_param_spec_map(self, value, expected):
        """A fractional gpus in the plugin config must not break runner construction."""
        runner = _make_runner({"gpus": value})
        assert runner.runner_params["gpus"] == expected


class TestGetGpus:
    """GoogleCloudBatchJobRunner._get_gpus resolution."""

    def test_resource_param_wins(self):
        runner = _make_runner()
        assert runner._get_gpus({"gpus": 1}, {"gpus": 2}) == 2

    def test_params_used_when_no_resource_param(self):
        runner = _make_runner()
        assert runner._get_gpus({"gpus": 1}, {}) == 1

    def test_defaults_to_zero(self):
        runner = _make_runner()
        assert runner._get_gpus({}, {}) == 0

    def test_zero_is_not_overridden_by_falsy_resource_param(self):
        runner = _make_runner()
        assert runner._get_gpus({"gpus": 0}, {"gpus": 0}) == 0

    @pytest.mark.parametrize(
        "value,expected",
        [("0", 0), ("1", 1), ("0.25", 1), ("0.5", 1), ("2", 2)],
    )
    def test_string_and_fractional_destination_values(self, value, expected):
        """TPV forwards gpus through param interpolation, so params holds strings."""
        runner = _make_runner()
        assert runner._get_gpus({"gpus": value}, {}) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [("0", 0), ("1", 1), ("0.25", 1), ("2", 2)],
    )
    def test_string_and_fractional_resource_values(self, value, expected):
        runner = _make_runner()
        assert runner._get_gpus({}, {"gpus": value}) == expected

    def test_fractional_resource_param_wins_over_destination(self):
        """A fractional request is truthy after rounding, so it must still take precedence."""
        runner = _make_runner()
        assert runner._get_gpus({"gpus": "2"}, {"gpus": "0.25"}) == 1


TEST_JOB_FILE = "/mnt/nfs/jobs_directory/000/42/galaxy_42.sh"


def _fake_job_wrapper(destination_params=None, resource_params=None, tool_id="image_learner"):
    """A stand-in for the JobWrapper attributes the spec/script builders touch."""
    destination_params = destination_params if destination_params is not None else {}
    resource_params = resource_params if resource_params is not None else {}
    return cast(
        Any,
        SimpleNamespace(
            job_id=42,
            tool=SimpleNamespace(id=tool_id, version="1.0"),
            job_destination=SimpleNamespace(id="gcp_batch", tags=None, params=destination_params),
            get_id_tag=lambda: "42",
            get_resource_parameters=lambda: resource_params,
        ),
    )


def _fake_ajs(job_wrapper):
    return cast(Any, SimpleNamespace(job_file=TEST_JOB_FILE, job_wrapper=job_wrapper))


class TestContainerScriptGpuFlag:
    """The container must be started with --gpus, the analog of Singularity's --nv;
    without it a GPU job runs blind to the device on a correctly provisioned G2 VM."""

    def _render(self, gpus=None):
        runner = _make_runner()
        job_wrapper = _fake_job_wrapper()
        args = (job_wrapper, _fake_ajs(job_wrapper), {}, "quay.io/example/tool:1.0", 4000, 8192)
        if gpus is None:
            # Exercise the default argument as well as the explicit one.
            return runner._create_container_execution_script(*args)
        return runner._create_container_execution_script(*args, gpus)

    @pytest.mark.parametrize("gpus", [1, 2, 4, 8])
    def test_gpu_flag_rendered_when_gpus_requested(self, gpus):
        assert "--gpus all" in self._render(gpus)

    def test_no_gpu_flag_for_cpu_jobs(self):
        """Guards every existing CPU job against a regression in the GPU branch."""
        assert "--gpus" not in self._render(0)

    def test_no_gpu_flag_by_default(self):
        assert "--gpus" not in self._render()

    def test_script_still_renders_the_docker_run(self):
        """string.Template raises KeyError on an unmapped placeholder, so a missing
        template_params entry would break script generation entirely."""
        script = self._render(1)
        assert "docker run --rm  --gpus all" in script
        assert "quay.io/example/tool:1.0" in script
        assert TEST_JOB_FILE in script


def _spec_runner(runner_params=None):
    """A runner able to build a batch job spec: no GCP client, no container finder."""
    runner = _make_runner(runner_params)
    runner.app = cast(Any, SimpleNamespace(config=SimpleNamespace(server_name="handler0")))
    runner._get_container_image = lambda job_wrapper: "quay.io/example/tool:1.0"  # type: ignore[method-assign]
    return runner


def _build_spec(destination_params, runner_params=None):
    runner = _spec_runner(runner_params)
    job_wrapper = _fake_job_wrapper(destination_params=destination_params)
    params = runner._get_job_params(job_wrapper.job_destination)
    return runner._create_batch_job_spec(job_wrapper, _fake_ajs(job_wrapper), params)


# A GPU tool as TPV forwards it: every value arrives as an interpolated string.
GPU_DESTINATION_PARAMS = {"gpus": "1", "cores": "32", "mem": "116"}


class TestCreateBatchJobSpecGpu:
    """End to end through _create_batch_job_spec: a TPV GPU request has to reach both
    the machine type and the docker run inside the generated script."""

    def test_gpu_request_selects_g2_machine_type_and_gpu_flag(self):
        job = _build_spec(GPU_DESTINATION_PARAMS)

        instance = job.allocation_policy.instances[0]
        assert instance.policy.machine_type == "g2-standard-32"
        assert "--gpus all" in job.task_groups[0].task_spec.runnables[0].script.text

    def test_cpu_job_gets_neither(self):
        job = _build_spec({"cores": "2", "mem": "4"})

        instance = job.allocation_policy.instances[0]
        assert not instance.policy.machine_type.startswith("g2-")
        assert not instance.install_gpu_drivers
        assert "--gpus" not in job.task_groups[0].task_spec.runnables[0].script.text

    def test_fractional_gpu_request_selects_a_whole_gpu_shape(self):
        """gpus: 0.25 means a share of a GPU; GCP Batch can only attach a whole L4."""
        job = _build_spec({"gpus": "0.25", "cores": "4", "mem": "16"})

        assert job.allocation_policy.instances[0].policy.machine_type == "g2-standard-4"

    def test_unsupported_gpu_count_raises_naming_the_supported_set(self):
        """queue_job turns this into the job's failure message, so it has to be legible."""
        with pytest.raises(ValueError, match=r"3 L4 GPU\(s\) is not supported"):
            _build_spec({"gpus": "3", "cores": "4", "mem": "16"})


class TestInstallGpuDrivers:
    """A custom VM image can have the L4 drivers baked in, in which case Batch must be
    told to skip the boot-time driver install."""

    def test_defaults_to_installing_drivers(self):
        job = _build_spec(GPU_DESTINATION_PARAMS)
        assert job.allocation_policy.instances[0].install_gpu_drivers is True

    @pytest.mark.parametrize("value", [False, "false", "False", "no", "0"])
    def test_destination_can_disable_the_driver_install(self, value):
        """Destination params bypass the runner param spec mapping and arrive as strings,
        so bool() would read "false" as True and install the drivers anyway."""
        job = _build_spec({**GPU_DESTINATION_PARAMS, "install_gpu_drivers": value})
        assert job.allocation_policy.instances[0].install_gpu_drivers is False

    @pytest.mark.parametrize("value", [True, "true", "True", "yes", "1"])
    def test_destination_can_enable_the_driver_install(self, value):
        job = _build_spec({**GPU_DESTINATION_PARAMS, "install_gpu_drivers": value})
        assert job.allocation_policy.instances[0].install_gpu_drivers is True

    @pytest.mark.parametrize("value,expected", [("false", False), ("true", True)])
    def test_runner_config_can_disable_the_driver_install(self, value, expected):
        """Runner config values go through the param spec map, which must also parse
        the string rather than applying bool()."""
        job = _build_spec(GPU_DESTINATION_PARAMS, runner_params={"install_gpu_drivers": value})
        assert job.allocation_policy.instances[0].install_gpu_drivers is expected
