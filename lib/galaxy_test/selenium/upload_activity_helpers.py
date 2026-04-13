"""Helper classes for testing the Upload Activity.

This module provides a fluent API for testing using the new Upload Activity
in Galaxy.

Example usage:
    # Simple upload
    self.upload_activity().stage_local_file("1.sam").start()

    # Multiple items with metadata
    (self.upload_activity()
        .stage_local_file("1.sam", name="file1", extension="sam", dbkey="hg18")
        .stage_local_file("2.txt", name="file2", extension="txt")
        .start())

    # Staged manipulation
    uploader = self.upload_activity()
    item = uploader.stage_paste_content("data")
    item.set_name("my_dataset")
    item.set_deferred(True)
    uploader.start()
"""

from typing import (
    Literal,
    Optional,
    TypedDict,
    TypeVar,
)

from .framework import NavigatesGalaxyMixin

T = TypeVar("T", bound="UploadItem")

UploadMethodId = Literal["local-file", "paste-content", "paste-links"]


class UploadMetadata(TypedDict, total=False):
    name: str
    extension: str
    dbkey: str
    deferred: bool


class UploadItem:
    """Represents a single item staged for upload.

    This class provides methods to manipulate the metadata of a staged upload
    item before executing the upload. Items are created by calling stage methods
    on an UploadContext.

    Attributes:
        index: The index of this item in the staged items list (0-based)
        context: The UploadContext this item belongs to
    """

    def __init__(self, index: int, context: "UploadContext"):
        """Initialize a new UploadItem.

        Args:
            index: The index of this staged item (0-based)
            context: The UploadContext this item belongs to
        """
        self.index = index
        self.context = context

    def set_name(self, name: str) -> "UploadItem":
        """Set the name for this upload item."""
        input_field = self.context._row_name_input(self.index).wait_for_visible()
        input_field.clear()
        input_field.send_keys(name)
        return self

    def set_extension(self, extension: str) -> "UploadItem":
        """Set the file format/extension for this upload item."""
        component = self.context._row_extension_select(self.index).wait_for_visible()
        self.context.driver_wrapper.select_set_value(component, extension)
        return self

    def set_dbkey(self, dbkey: str) -> "UploadItem":
        """Set the reference genome/dbkey for this upload item."""
        component = self.context._row_dbkey_select(self.index).wait_for_visible()
        self.context.driver_wrapper.select_set_value(component, dbkey)
        return self

    def set_deferred(self, deferred: bool) -> "UploadItem":
        """Set whether this upload should be deferred."""
        checkbox = self.context._row_deferred_checkbox(self.index)
        if checkbox is None:
            if deferred:
                raise AssertionError("Deferred is not available for the current Upload Activity method")
            return self

        is_checked = checkbox.is_selected()
        if deferred != is_checked:
            self.context._row_deferred_label(self.index).wait_for_and_click()
        return self

    def set_content(self, content: str) -> "UploadItem":
        """Set per-item content text in methods that expose a row textarea."""
        if self.context._current_method_id != "paste-content":
            raise AssertionError("Per-item content editing is only available for the paste-content method")

        textarea_target = self.context.components.beta_upload.paste_content_row_textarea(
            row=self.context._row_number(self.index)
        )
        if textarea_target.is_absent or not textarea_target.is_displayed:
            self.context.components.beta_upload.paste_content_row_toggle_button(
                row=self.context._row_number(self.index)
            ).wait_for_and_click()
        textarea = textarea_target.wait_for_visible()
        textarea.clear()
        textarea.send_keys(content)
        return self

    def start(self) -> None:
        """Start the upload for this item (and any other staged items)."""
        self.context.start()

    def remove(self) -> None:
        """Remove this item from the staged items list."""
        self.context._row_remove_button(self.index).wait_for_and_click()


class LocalUploadItem(UploadItem):
    def stage_local_file(self, test_path: str, metadata: Optional["UploadMetadata"] = None) -> "LocalUploadItem":
        """Stage another local file and return the new item."""
        return self.context.stage_local_file(test_path, metadata)


class PasteContentUploadItem(UploadItem):
    def stage_paste_content(
        self, content: str, metadata: Optional["UploadMetadata"] = None
    ) -> "PasteContentUploadItem":
        """Stage another paste content and return the new item."""
        return self.context.stage_paste_content(content, metadata)


class UploadContext:
    """Manages an upload session with staging and execution."""

    def __init__(self, method_id: UploadMethodId, driver_wrapper: NavigatesGalaxyMixin):
        """Initialize a new UploadContext."""
        self.driver_wrapper = driver_wrapper
        self._item_count = 0
        self._current_method_id: Optional[UploadMethodId] = None

        # Navigate to the upload method
        self.driver_wrapper.home()
        self.driver_wrapper.components.tools.activity.wait_for_visible()
        self.driver_wrapper.components.preferences.activity.wait_for_and_click()
        self.driver_wrapper.components.beta_upload.activity.wait_for_and_click()
        self._select_method(method_id)

    @property
    def components(self):
        """Access to component selectors."""
        return self.driver_wrapper.components

    def stage_local_file(self, test_path: str, metadata: Optional["UploadMetadata"] = None) -> LocalUploadItem:
        """Stage a local file for upload. Returns the new item."""
        # Input is intentionally hidden (d-none), so do not wait for visible state
        file_input = self.driver_wrapper.wait_for_selector("#local-file-input")

        # Playwright needs element-handle file setting for hidden inputs.
        if self.driver_wrapper.backend_type == "playwright":
            file_input.element_handle.set_input_files(test_path)
        else:
            file_input.send_keys(test_path)

        return self._create_item(LocalUploadItem, metadata)

    def stage_paste_content(self, content: str, metadata: Optional["UploadMetadata"] = None) -> PasteContentUploadItem:
        """Stage text content for upload. Returns the new item."""
        textarea = self.components.beta_upload.paste_content_textarea.wait_for_visible()
        textarea.click()
        textarea.send_keys(content)

        return self._create_item(PasteContentUploadItem, metadata)

    def stage_paste_link(self, url: str, metadata: Optional["UploadMetadata"] = None) -> UploadItem:
        """Stage a file link URL for upload. Returns the new item.

        You cannot chain-stage multiple links with this method - use stage_paste_links instead. This is for single URLs only.
        """
        textarea = self.components.beta_upload.paste_textarea.wait_for_visible()
        textarea.click()
        textarea.send_keys(url)
        self.components.beta_upload.add_urls_button.wait_for_and_click()

        return self._create_item(UploadItem, metadata)

    def stage_paste_links(self, url_metadata_pairs: list[tuple[str, Optional["UploadMetadata"]]]) -> "UploadContext":
        """Stage multiple file link URLs for upload, each with optional metadata.

        Args:
            url_metadata_pairs: List of (url, metadata) tuples where metadata is optional.
                Example: [(url1, {"name": "link1", "extension": "txt"}), (url2, None)]

        Returns:
            self for method chaining
        """
        urls = [pair[0] for pair in url_metadata_pairs]
        textarea = self.components.beta_upload.paste_textarea.wait_for_visible()
        textarea.click()
        textarea.send_keys("\n".join(urls))
        self.components.beta_upload.add_urls_button.wait_for_and_click()

        # Apply metadata to each item
        start_index = self._item_count
        for i, (_, metadata) in enumerate(url_metadata_pairs):
            if metadata is not None:
                item = UploadItem(start_index + i, self)
                if "name" in metadata:
                    item.set_name(metadata["name"])
                if "extension" in metadata:
                    item.set_extension(metadata["extension"])
                if "dbkey" in metadata:
                    item.set_dbkey(metadata["dbkey"])
                if "deferred" in metadata:
                    item.set_deferred(metadata["deferred"])

        self._item_count += len(url_metadata_pairs)
        return self

    def _create_item(self, item_class: type[T], metadata: Optional["UploadMetadata"] = None) -> T:
        """Create and optionally configure a new UploadItem."""
        if metadata is None:
            metadata = {}

        item = item_class(self._item_count, self)
        self._item_count += 1

        if "name" in metadata:
            item.set_name(metadata["name"])
        if "extension" in metadata:
            item.set_extension(metadata["extension"])
        if "dbkey" in metadata:
            item.set_dbkey(metadata["dbkey"])
        if "deferred" in metadata:
            item.set_deferred(metadata["deferred"])

        return item

    def start(self) -> None:
        """Execute the upload with all staged items."""
        self.components.beta_upload.start_button.wait_for_and_click()

    def cancel(self) -> None:
        """Cancel all staged items without uploading."""
        self.components.beta_upload.cancel_button.wait_for_and_click()

    def _select_method(self, method_id: UploadMethodId) -> None:
        if self._current_method_id == method_id:
            return
        self.components.beta_upload.method_card(method_id=method_id).wait_for_and_click()
        self._current_method_id = method_id

    def _row_number(self, index: int) -> int:
        return index + 1

    def _row_name_input(self, index: int):
        row = self._row_number(index)
        return self.components.beta_upload.row_name_input(row=row)

    def _row_extension_select(self, index: int):
        row = self._row_number(index)
        return self.components.beta_upload.row_extension_select(row=row)

    def _row_dbkey_select(self, index: int):
        row = self._row_number(index)
        return self.components.beta_upload.row_dbkey_select(row=row)

    def _row_remove_button(self, index: int):
        row = self._row_number(index)
        return self.components.beta_upload.row_remove_button(row=row)

    def _row_deferred_checkbox(self, index: int):
        if self._current_method_id != "paste-links":
            raise AssertionError("Deferred option is only available for the paste-links method")
        row = self._row_number(index)
        return self.components.beta_upload.paste_links_row_deferred_checkbox(row=row).wait_for_present()

    def _row_deferred_label(self, index: int):
        if self._current_method_id != "paste-links":
            raise AssertionError("Deferred label is only available for the paste-links method")
        row = self._row_number(index)
        return self.components.beta_upload.paste_links_row_deferred_label(row=row)


class UsesUploadActivity(NavigatesGalaxyMixin):
    """Mixin for using the Upload Activity in the testing framework."""

    def upload_context(self, method_id: UploadMethodId) -> UploadContext:
        """Create an upload context for the specified method.

        Args:
            method_id: The upload method to use

        Returns:
            An UploadContext object for staging and executing uploads
        """
        return UploadContext(method_id, self)
