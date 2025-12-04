from typing import Any

from galaxy.datatypes.images import (
    Dicom,
    Image,
    Pdf,
    Png,
    Tiff,
)
from galaxy.datatypes.sniff import get_test_fname
from .util import (
    get_dataset,
    MockDatasetDataset,
)

# Define test decorator


def __test(image_cls: type[Image], input_filename: str):

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


def __create_test(image_cls: type[Image], input_filename: str, **expected_metadata: Any):

    @__test(image_cls, input_filename)
    def test(metadata):
        for metadata_key, expected_value in expected_metadata.items():
            metadata_value = getattr(metadata, metadata_key)
            cond = (
                (metadata_value is expected_value)
                if expected_value is None or type(expected_value) is bool
                else (metadata_value == expected_value)
            )
            assert cond, f"expected: {repr(expected_value)}, actual: {repr(metadata_value)}"

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


# Tests for `Tiff` class

test_tiff_axes_yx = __create_test(Tiff, "im1_uint8.tif", axes="YX")
test_tiff_axes_zcyx = __create_test(Tiff, "im6_uint8.tif", axes="ZCYX")
test_tiff_dtype_uint8 = __create_test(Tiff, "im6_uint8.tif", dtype="uint8")
test_tiff_dtype_uint16 = __create_test(Tiff, "im8_uint16.tif", dtype="uint16")
test_tiff_dtype_float64 = __create_test(Tiff, "im4_float.tif", dtype="float64")
test_tiff_num_unique_values_2 = __create_test(Tiff, "im3_b.tif", num_unique_values=2)
test_tiff_num_unique_values_618 = __create_test(Tiff, "im4_float.tif", num_unique_values=618)
test_tiff_width_16 = __create_test(Tiff, "im7_uint8.tif", width=16)  # axes: ZYX
test_tiff_width_32 = __create_test(Tiff, "im3_b.tif", width=32)  # axes: YXS
test_tiff_height_8 = __create_test(Tiff, "im7_uint8.tif", height=8)  # axes: ZYX
test_tiff_height_32 = __create_test(Tiff, "im3_b.tif", height=32)  # axes: YXS
test_tiff_channels_0 = __create_test(Tiff, "im1_uint8.tif", channels=0)
test_tiff_channels_2 = __create_test(Tiff, "im5_uint8.tif", channels=2)  # axes: CYX
test_tiff_channels_3 = __create_test(Tiff, "im3_b.tif", channels=3)  # axes: YXS
test_tiff_depth_0 = __create_test(Tiff, "im1_uint8.tif", depth=0)  # axes: YXS
test_tiff_depth_25 = __create_test(Tiff, "im7_uint8.tif", depth=25)  # axes: ZYX
test_tiff_frames_0 = __create_test(Tiff, "im1_uint8.tif", frames=0)  # axes: YXS
test_tiff_frames_5 = __create_test(Tiff, "im8_uint16.tif", frames=5)  # axes: TYX


@__test(Tiff, "im_empty.tif")
def test_tiff_empty(metadata):
    __assert_empty_metadata(metadata)


test_tiff_unsupported_compression = __create_test(
    Tiff,
    "1.tiff",
    # If the compression of a TIFF is unsupported, some fields should still be there
    axes="YX",
    dtype="bool",
    width=1728,
    height=2376,
    channels=0,
    depth=0,
    frames=0,
    # The other fields should be missing
    num_unique_values=None,
)


test_tiff_unsupported_multiseries = __create_test(
    Tiff,
    "im9_multiseries.tif",  # TODO: rename to .tiff
    axes=["YXS", "YX"],
    dtype=["uint8", "uint16"],
    num_unique_values=[2, 255],
    width=[32, 256],
    height=[32, 256],
    channels=[3, 0],
    depth=[0, 0],
    frames=[0, 0],
)


# Tests for `Image` class

test_png_axes_yx = __create_test(Image, "im1_uint8.png", axes="YX")
test_png_axes_yxc = __create_test(Image, "im3_a.png", axes="YXC")
test_png_dtype_uint8 = __create_test(Image, "im1_uint8.png", dtype="uint8")
test_png_num_unique_values_1 = __create_test(Image, "im2_a.png", num_unique_values=None)
test_png_num_unique_values_2 = __create_test(Image, "im2_b.png", num_unique_values=None)
test_png_width_32 = __create_test(Image, "im2_b.png", width=32)
test_png_height_32 = __create_test(Image, "im2_b.png", height=32)
test_png_channels_0 = __create_test(Image, "im1_uint8.png", channels=0)
test_png_channels_3 = __create_test(Image, "im3_a.png", channels=3)
test_png_depth_0 = __create_test(Image, "im1_uint8.png", depth=0)
test_png_frames_1 = __create_test(Image, "im1_uint8.png", frames=1)


# Tests for `Png` class

test_png_axes_yx = __create_test(Png, "im1_uint8.png", axes="YX")
test_png_axes_yxc = __create_test(Png, "im3_a.png", axes="YXC")
test_png_dtype_uint8 = __create_test(Png, "im1_uint8.png", dtype="uint8")
test_png_num_unique_values_1 = __create_test(Png, "im2_a.png", num_unique_values=1)
test_png_num_unique_values_2 = __create_test(Png, "im2_b.png", num_unique_values=2)
test_png_width_32 = __create_test(Png, "im2_b.png", width=32)
test_png_height_32 = __create_test(Png, "im2_b.png", height=32)
test_png_channels_0 = __create_test(Png, "im1_uint8.png", channels=0)
test_png_channels_3 = __create_test(Png, "im3_a.png", channels=3)
test_png_depth_0 = __create_test(Png, "im1_uint8.png", depth=0)
test_png_frames_1 = __create_test(Png, "im1_uint8.png", frames=1)


# Tests for `Dicom` class

test_2d_singlechannel = __create_test(
    Dicom,
    "ct_image.dcm",
    width=128,
    height=128,
    channels=1,
    dtype="int16",
    num_unique_values=None,
    is_tiled=False,
)


test_tiled_multichannel = __create_test(
    Dicom,
    "sm_image.dcm",
    width=50,
    height=50,
    channels=3,
    dtype="uint8",
    num_unique_values=None,
    is_tiled=True,
)


test_3d_binary = __create_test(
    Dicom,
    "seg_image_ct_binary.dcm",
    width=16,
    height=16,
    channels=1,
    dtype="bool",
    num_unique_values=2,
    is_tiled=False,
)


def test_dicom_sniff():
    fname = get_test_fname("ct_image.dcm")
    assert Dicom().sniff(fname)


# Test with files that neither Pillow, tifffile, nor pydicom can open


@__test(Pdf, "454Score.pdf")
def test_unsupported_metadata(metadata):
    __assert_empty_metadata(metadata)
