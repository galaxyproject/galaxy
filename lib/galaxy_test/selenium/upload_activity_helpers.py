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
    overload,
    TypedDict,
    TypeVar,
    Union,
)

from .framework import NavigatesGalaxyMixin

T = TypeVar("T", bound="UploadItem")

UploadMethodId = Literal[
    "local-file",
    "paste-content",
    "paste-links",
    "remote-files",
    "composite-file",
    "data-library",
]


class UploadMetadata(TypedDict, total=False):
    name: str
    extension: str
    dbkey: str
    deferred: bool


class UploadItem:
    """Represents a single item staged for upload."""

    def __init__(self, index: int, context: "UploadContext"):
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


class RemoteFileUploadItem(UploadItem):
    def stage_remote_file(
        self, source_label: str, file_label: str, metadata: Optional["UploadMetadata"] = None
    ) -> "RemoteFileUploadItem":
        """Stage another remote file and return the new item."""
        return self.context.stage_remote_file(source_label, file_label, metadata)


class DataLibraryUploadItem(UploadItem):
    def stage_data_library_dataset(self, library_label: str, dataset_label: str) -> "DataLibraryUploadItem":
        """Stage another data library dataset and return the new item."""
        return self.context.stage_data_library_dataset(library_label, dataset_label)


class UploadContext:

    def __init__(self, method_id: UploadMethodId, driver_wrapper: NavigatesGalaxyMixin):
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

    def stage_remote_file(
        self, source_label: str, file_label: str, metadata: Optional["UploadMetadata"] = None
    ) -> RemoteFileUploadItem:
        """Stage a single remote file via the remote-files upload method.

        Args:
            source_label: Display label of the remote file source (for example "Posix").
            file_label: Display label of the file to stage from inside that source.
            metadata: Optional dataset metadata to apply after staging.

        Returns:
            RemoteFileUploadItem for the staged remote file.
        """
        if self._current_method_id != "remote-files":
            raise AssertionError("stage_remote_file is only available for the remote-files method")

        # Navigate into the source by clicking its label
        self.components.beta_upload.remote_files_browser_label(label=source_label).wait_for_and_click()
        # Wait for the file list to load and become visible
        self.components.beta_upload.remote_files_browser_label(label=file_label).wait_for_visible()
        # Select the file by clicking its label (toggles selection)
        self.components.beta_upload.remote_files_browser_label(label=file_label).wait_for_and_click()
        # Click "Add Selected Files" button
        self.components.beta_upload.remote_files_add_selected.wait_for_and_click()
        return self._create_item(RemoteFileUploadItem, metadata)

    def stage_data_library_dataset(self, library_label: str, dataset_label: str) -> DataLibraryUploadItem:
        """Stage a single dataset from a data library via the data-library method.

        Args:
            library_label: Display name of the library to open.
            dataset_label: Display name of the dataset to select and stage.
            metadata: Optional dataset metadata to apply after staging.

        Returns:
            DataLibraryUploadItem for the staged library dataset.
        """
        if self._current_method_id != "data-library":
            raise AssertionError("stage_data_library_dataset is only available for the data-library method")

        self.components.beta_upload.data_library_library_label(label=library_label).wait_for_and_click()
        self.components.beta_upload.data_library_item_label(label=dataset_label).wait_for_and_click()
        self.components.beta_upload.data_library_add_selected.wait_for_and_click()
        return self._create_item(DataLibraryUploadItem)

    def select_composite(self, composite_type: str) -> "UploadContext":
        """Select composite datatype in the composite-file method."""
        if self._current_method_id != "composite-file":
            raise AssertionError("select_composite is only available for the composite-file method")

        self._select_composite_type(composite_type)
        return self

    def stage_composite_url_slot(self, slot: int, url: str) -> "UploadContext":
        """Set a composite slot to URL mode and populate its URL."""
        if self._current_method_id != "composite-file":
            raise AssertionError("stage_composite_url_slot is only available for the composite-file method")
        if slot < 1:
            raise AssertionError("slot must be >= 1")

        self._select_composite_slot_mode(row=slot, mode="url")
        url_input = self.components.beta_upload.composite_slot_url_input(row=slot).wait_for_visible()
        url_input.clear()
        url_input.send_keys(url)
        return self

    def stage_composite_paste_slot(self, slot: int, content: str) -> "UploadContext":
        """Set a composite slot to paste mode and populate content."""
        if self._current_method_id != "composite-file":
            raise AssertionError("stage_composite_paste_slot is only available for the composite-file method")
        if slot < 1:
            raise AssertionError("slot must be >= 1")

        self._select_composite_slot_mode(row=slot, mode="paste")
        paste_textarea = self.components.beta_upload.composite_slot_paste_textarea(row=slot).wait_for_visible()
        paste_textarea.clear()
        paste_textarea.send_keys(content)
        return self

    def stage_composite_file_slot(self, slot: int, file_path: str) -> "UploadContext":
        """Set a composite slot to local-file mode and attach a file path."""
        if self._current_method_id != "composite-file":
            raise AssertionError("stage_composite_file_slot is only available for the composite-file method")
        if slot < 1:
            raise AssertionError("slot must be >= 1")

        self._select_composite_slot_mode(row=slot, mode="local")
        file_input = self.components.beta_upload.composite_slot_file_input(row=slot).wait_for_present()
        if self.driver_wrapper.backend_type == "playwright":
            file_input.element_handle.set_input_files(file_path)
        else:
            file_input.send_keys(file_path)
        return self

    def _select_composite_type(self, composite_type: str) -> None:
        composite_type_lower = composite_type.lower()
        self.components.beta_upload.composite_type_enabled_dropdown.wait_for_and_click()

        visible_options = self.components.beta_upload.composite_type_options_visible.all()
        candidates: list[tuple[str, str]] = []
        for option in visible_options:
            option_id = option.get_attribute("data-id") or ""
            option_label = (option.get_attribute("data-label") or option.text or "").strip()
            if option_id:
                candidates.append((option_id, option_label))

        target_id: Optional[str] = None
        for option_id, option_label in candidates:
            if option_id.lower() == composite_type_lower or option_label.lower() == composite_type_lower:
                target_id = option_id
                break
        if target_id is None:
            for option_id, option_label in candidates:
                if composite_type_lower in option_label.lower():
                    target_id = option_id
                    break
        if target_id is None and candidates:
            target_id = candidates[0][0]

        if not target_id:
            raise AssertionError(f"No composite type candidates found for '{composite_type}'")

        self.components.beta_upload.composite_type_option_by_id_visible(id=target_id).wait_for_and_click()
        try:
            self.components.beta_upload.composite_first_slot.wait_for_visible(timeout=5)
        except Exception as exc:
            raise AssertionError(
                f"Composite slots did not render after selecting '{composite_type}'. Candidates: {candidates}"
            ) from exc

    def _select_composite_slot_mode(self, row: int, mode: Literal["local", "url", "paste"]) -> None:
        if mode == "local":
            visible_action_target = self.components.beta_upload.composite_slot_enter_local_action_visible
            input_target = self.components.beta_upload.composite_slot_file_input(row=row)
        elif mode == "url":
            visible_action_target = self.components.beta_upload.composite_slot_enter_url_action_visible
            input_target = self.components.beta_upload.composite_slot_url_input(row=row)
        else:
            visible_action_target = self.components.beta_upload.composite_slot_enter_paste_action_visible
            input_target = self.components.beta_upload.composite_slot_paste_textarea(row=row)

        for _ in range(2):
            dropdown = self.components.beta_upload.composite_slot_mode_dropdown(row=row).wait_for_visible()
            if dropdown.get_attribute("aria-expanded") != "true":
                try:
                    dropdown.click()
                except Exception:
                    self.driver_wrapper.action_chains().move_to_element(dropdown).click().perform()

            action_element = visible_action_target.wait_for_visible()
            try:
                action_element.click()
            except Exception:
                self.driver_wrapper.action_chains().move_to_element(action_element).click().perform()

            if mode == "local":
                return
            if input_target.is_displayed:
                return

        # Let the underlying wait raise a clear timeout if mode was not applied.
        input_target.wait_for_visible()

    def select_target_history(self, history_id: str) -> "UploadContext":
        """Change the upload target history using the TargetHistorySelector UI."""
        self.components.beta_upload.target_history_change_link.wait_for_and_click()
        self.components.beta_upload.history_selector_modal_item(history_id=history_id).wait_for_and_click()
        # Wait for modal to dismiss before proceeding
        self.components.beta_upload.history_selector_modal.wait_for_absent_or_hidden()
        return self

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


# Mode-specific context classes that provide restricted APIs
class BaseUploadContext:
    """Base context with common methods shared across all upload modes."""

    def __init__(self, context: UploadContext):
        self._context = context

    def start(self) -> None:
        self._context.start()

    def cancel(self) -> None:
        """Cancel all staged items without uploading."""
        self._context.cancel()

    def select_target_history(self, history_id: str) -> "BaseUploadContext":
        """Change the upload target history using the TargetHistorySelector UI."""
        self._context.select_target_history(history_id)
        return self


class LocalFileContext(BaseUploadContext):

    def stage_local_file(self, test_path: str, metadata: Optional["UploadMetadata"] = None) -> LocalUploadItem:
        return self._context.stage_local_file(test_path, metadata)

    def select_target_history(self, history_id: str) -> "LocalFileContext":

        self._context.select_target_history(history_id)
        return self


class PasteContentContext(BaseUploadContext):

    def stage_paste_content(self, content: str, metadata: Optional["UploadMetadata"] = None) -> PasteContentUploadItem:
        return self._context.stage_paste_content(content, metadata)

    def select_target_history(self, history_id: str) -> "PasteContentContext":
        """Change the upload target history using the TargetHistorySelector UI."""
        self._context.select_target_history(history_id)
        return self


class PasteLinksContext(BaseUploadContext):
    """Restricted context for paste link uploads only."""

    def stage_paste_link(self, url: str, metadata: Optional["UploadMetadata"] = None) -> UploadItem:
        """Stage a file link URL for upload. Returns the new item.

        You cannot chain-stage multiple links with this method - use stage_paste_links instead. This is for single URLs only.
        """
        return self._context.stage_paste_link(url, metadata)

    def stage_paste_links(
        self, url_metadata_pairs: list[tuple[str, Optional["UploadMetadata"]]]
    ) -> "PasteLinksContext":
        """Stage multiple file link URLs for upload, each with optional metadata.

        Args:
            url_metadata_pairs: List of (url, metadata) tuples where metadata is optional.
                Example: [(url1, {"name": "link1", "extension": "txt"}), (url2, None)]

        Returns:
            self for method chaining
        """
        self._context.stage_paste_links(url_metadata_pairs)
        return self

    def select_target_history(self, history_id: str) -> "PasteLinksContext":
        """Change the upload target history using the TargetHistorySelector UI."""
        self._context.select_target_history(history_id)
        return self


class RemoteFilesContext(BaseUploadContext):

    def stage_remote_file(
        self, source_label: str, file_label: str, metadata: Optional["UploadMetadata"] = None
    ) -> RemoteFileUploadItem:
        return self._context.stage_remote_file(source_label, file_label, metadata)

    def select_target_history(self, history_id: str) -> "RemoteFilesContext":
        """Change the upload target history using the TargetHistorySelector UI."""
        self._context.select_target_history(history_id)
        return self


class CompositeFileContext(BaseUploadContext):

    def select_composite(self, composite_type: str) -> "CompositeFileContext":
        """Select composite datatype in the composite-file method."""
        self._context.select_composite(composite_type)
        return self

    def stage_composite_url_slot(self, slot: int, url: str) -> "CompositeFileContext":
        """Set a composite slot to URL mode and populate its URL."""
        self._context.stage_composite_url_slot(slot, url)
        return self

    def stage_composite_paste_slot(self, slot: int, content: str) -> "CompositeFileContext":
        """Set a composite slot to paste mode and populate content."""
        self._context.stage_composite_paste_slot(slot, content)
        return self

    def stage_composite_file_slot(self, slot: int, file_path: str) -> "CompositeFileContext":
        """Set a composite slot to local-file mode and attach a file path."""
        self._context.stage_composite_file_slot(slot, file_path)
        return self

    def select_target_history(self, history_id: str) -> "CompositeFileContext":
        """Change the upload target history using the TargetHistorySelector UI."""
        self._context.select_target_history(history_id)
        return self


class DataLibraryContext(BaseUploadContext):

    def stage_data_library_dataset(self, library_label: str, dataset_label: str) -> DataLibraryUploadItem:
        return self._context.stage_data_library_dataset(library_label, dataset_label)

    def select_target_history(self, history_id: str) -> "DataLibraryContext":
        """Change the upload target history using the TargetHistorySelector UI."""
        self._context.select_target_history(history_id)
        return self


# Mapping of upload method IDs to their corresponding context classes
_CONTEXT_CLASS_MAP: dict[UploadMethodId, type[BaseUploadContext]] = {
    "local-file": LocalFileContext,
    "paste-content": PasteContentContext,
    "paste-links": PasteLinksContext,
    "remote-files": RemoteFilesContext,
    "composite-file": CompositeFileContext,
    "data-library": DataLibraryContext,
}


class UsesUploadActivity(NavigatesGalaxyMixin):
    """Mixin for using the Upload Activity in the testing framework."""

    @overload
    def upload_context(self, method_id: Literal["local-file"]) -> LocalFileContext: ...

    @overload
    def upload_context(self, method_id: Literal["paste-content"]) -> PasteContentContext: ...

    @overload
    def upload_context(self, method_id: Literal["paste-links"]) -> PasteLinksContext: ...

    @overload
    def upload_context(self, method_id: Literal["remote-files"]) -> RemoteFilesContext: ...

    @overload
    def upload_context(self, method_id: Literal["composite-file"]) -> CompositeFileContext: ...

    @overload
    def upload_context(self, method_id: Literal["data-library"]) -> DataLibraryContext: ...

    def upload_context(self, method_id: UploadMethodId) -> Union[
        LocalFileContext,
        PasteContentContext,
        PasteLinksContext,
        RemoteFilesContext,
        CompositeFileContext,
        DataLibraryContext,
    ]:
        """Create an upload context for the specified method.

        Args:
            method_id: The upload method to use

        Returns:
            A mode-specific context object for staging and executing uploads.
        """
        base_context = UploadContext(method_id, self)
        context_class = _CONTEXT_CLASS_MAP[method_id]
        # mypy cannot infer the return type here due to the dynamic mapping,
        # but the overloads provide correct type hints for callers
        return context_class(base_context)  # type: ignore[return-value]
