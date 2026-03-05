"""Unit tests for Google Cloud Batch job runner utility methods."""

import pytest

from galaxy.jobs.runners.util.gcp_batch import (
    convert_cpu_to_milli,
    convert_duration_to_seconds,
    convert_memory_to_mib,
    DEFAULT_MAX_RUN_DURATION,
    parse_docker_volumes_param,
    parse_volume_spec,
    parse_volumes_param,
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
        assert result["read_only"] is True

    def test_read_only_with_readonly(self):
        result = parse_volume_spec("server:/path:/mount:readonly")
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
