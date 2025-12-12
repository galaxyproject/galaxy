"""Unit tests for Google Cloud Batch job runner utility methods."""

import pytest

from galaxy.jobs.runners.gcp_batch import GoogleCloudBatchJobRunner


class TestSanitizeLabelValue:
    """Tests for _sanitize_label_value static method."""

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
        ],
    )
    def test_sanitize_label_value(self, input_value, expected):
        result = GoogleCloudBatchJobRunner._sanitize_label_value(input_value)
        assert result == expected


class TestConvertCpuToMilli:
    """Tests for _convert_cpu_to_milli method."""

    @pytest.fixture
    def runner(self):
        class MockRunner:
            pass

        return MockRunner()

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
    def test_convert_cpu_to_milli(self, runner, input_value, expected):
        result = GoogleCloudBatchJobRunner._convert_cpu_to_milli(runner, input_value)
        assert result == expected


class TestConvertMemoryToMib:
    """Tests for _convert_memory_to_mib method."""

    @pytest.fixture
    def runner(self):
        class MockRunner:
            pass

        return MockRunner()

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
    def test_convert_memory_to_mib(self, runner, input_value, expected):
        result = GoogleCloudBatchJobRunner._convert_memory_to_mib(runner, input_value)
        assert result == expected
