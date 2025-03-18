from typing import (
    Any,
    Type,
)

from galaxy.datatypes.images import (
    Image,
    Pdf,
    Png,
    Tiff,
)
from .util import (
    get_dataset,
    MockDatasetDataset,
)

# Define test decorator


def __test(image_cls: Type[Image], input_filename: str):

    def decorator(test_impl):

        def test():
            image = image_cls()
            with get_dataset(input_filename) as dataset:
                dataset.dataset = MockDatasetDataset(dataset.get_file_name())
                image.set_meta(dataset)
                test_impl(dataset.metadata)

        return test

    return decorator


# Define test factory


def __create_test(image_cls: Type[Image], input_filename: str, metadata_key: str, expected_value: Any):

    @__test(image_cls, input_filename)
    def test(metadata):
        assert getattr(metadata, metadata_key) == expected_value

    return test


# Define test utilities


def __assert_empty_metadata(metadata):
    for key in (
        "axes",
        "dtype",
        "num_unique_values",
        "width",
        "height",
        "channels",
        "depth",
        "frames",
    ):
        assert getattr(metadata, key, None) is None


# Tests with TIFF files

test_tiff_axes_yx = __create_test(Tiff, "im1_uint8.tif", "axes", "YX")
test_tiff_axes_zcyx = __create_test(Tiff, "im6_uint8.tif", "axes", "ZCYX")
test_tiff_dtype_uint8 = __create_test(Tiff, "im6_uint8.tif", "dtype", "uint8")
test_tiff_dtype_uint16 = __create_test(Tiff, "im8_uint16.tif", "dtype", "uint16")
test_tiff_dtype_float64 = __create_test(Tiff, "im4_float.tif", "dtype", "float64")
test_tiff_num_unique_values_2 = __create_test(Tiff, "im3_b.tif", "num_unique_values", 2)
test_tiff_num_unique_values_618 = __create_test(Tiff, "im4_float.tif", "num_unique_values", 618)
test_tiff_width_16 = __create_test(Tiff, "im7_uint8.tif", "width", 16)  # axes: ZYX
test_tiff_width_32 = __create_test(Tiff, "im3_b.tif", "width", 32)  # axes: YXS
test_tiff_height_8 = __create_test(Tiff, "im7_uint8.tif", "height", 8)  # axes: ZYX
test_tiff_height_32 = __create_test(Tiff, "im3_b.tif", "height", 32)  # axes: YXS
test_tiff_channels_0 = __create_test(Tiff, "im1_uint8.tif", "channels", 0)
test_tiff_channels_2 = __create_test(Tiff, "im5_uint8.tif", "channels", 2)  # axes: CYX
test_tiff_channels_3 = __create_test(Tiff, "im3_b.tif", "channels", 3)  # axes: YXS
test_tiff_depth_0 = __create_test(Tiff, "im1_uint8.tif", "depth", 0)  # axes: YXS
test_tiff_depth_25 = __create_test(Tiff, "im7_uint8.tif", "depth", 25)  # axes: ZYX
test_tiff_frames_0 = __create_test(Tiff, "im1_uint8.tif", "frames", 0)  # axes: YXS
test_tiff_frames_5 = __create_test(Tiff, "im8_uint16.tif", "frames", 5)  # axes: TYX


@__test(Tiff, "im_empty.tif")
def test_tiff_empty(metadata):
    __assert_empty_metadata(metadata)


@__test(Tiff, "1.tiff")
def test_tiff_unsupported_compression(metadata):
    # If the compression of a TIFF is unsupported, some fields should still be there
    assert metadata.axes == "YX"
    assert metadata.dtype == "bool"
    assert metadata.width == 1728
    assert metadata.height == 2376
    assert metadata.channels == 0
    assert metadata.depth == 0
    assert metadata.frames == 0

    # The other fields should be missing
    assert getattr(metadata, "num_unique_values", None) is None


@__test(Tiff, "im9_multiseries.tif")
def test_tiff_multiseries(metadata):
    assert metadata.axes == ["YXS", "YX"]
    assert metadata.dtype == ["uint8", "uint16"]
    assert metadata.num_unique_values == [2, 255]
    assert metadata.width == [32, 256]
    assert metadata.height == [32, 256]
    assert metadata.channels == [3, 0]
    assert metadata.depth == [0, 0]
    assert metadata.frames == [0, 0]


# Tests with PNG files

test_png_axes_yx = __create_test(Png, "im1_uint8.png", "axes", "YX")
test_png_axes_yxc = __create_test(Png, "im3_a.png", "axes", "YXC")
test_png_dtype_uint8 = __create_test(Png, "im1_uint8.png", "dtype", "uint8")
test_png_num_unique_values_1 = __create_test(Png, "im2_a.png", "num_unique_values", 1)
test_png_num_unique_values_2 = __create_test(Png, "im2_b.png", "num_unique_values", 2)
test_png_width_32 = __create_test(Png, "im2_b.png", "width", 32)
test_png_height_32 = __create_test(Png, "im2_b.png", "height", 32)
test_png_channels_0 = __create_test(Png, "im1_uint8.png", "channels", 0)
test_png_channels_3 = __create_test(Png, "im3_a.png", "channels", 3)
test_png_depth_0 = __create_test(Png, "im1_uint8.png", "depth", 0)
test_png_frames_1 = __create_test(Png, "im1_uint8.png", "frames", 1)


# Test with files that neither Pillow nor tifffile can open


@__test(Pdf, "454Score.pdf")
def test_unsupported_metadata(metadata):
    __assert_empty_metadata(metadata)
