"""Helper classes for testing the Upload Activity.

This module provides a fluent API for testing using the new Upload Activity
in Galaxy.

Example usage:
    # Simple upload
    self.upload_context("local-file").stage_local_file("1.sam").start()

    # Multiple items with metadata
    (self.upload_context("local-file")
        .stage_local_file("1.sam", {"name": "file1", "extension": "sam", "dbkey": "hg18"})
        .stage_local_file("2.txt", {"name": "file2", "extension": "txt"})
        .start())

    # Atomic list creation from staged files
    (self.upload_context("local-file")
        .stage_local_file("1.tabular")
        .stage_local_file("2.tabular")
        .to_list("My Upload List")
        .start())

    # Staged manipulation
    uploader = self.upload_context("paste-content")
    item = uploader.stage_paste_content("data")
    item.set_name("my_dataset")
    item.set_deferred(True)
    uploader.start()

    # Rule-based import
    (self.upload_context("rule")
        .creating("collections")
        .from_source("dataset_as_table")
        .select_dataset(1))
"""

from typing import (
    Literal,
    overload,
    TypedDict,
    TypeVar,
)

from .framework import NavigatesGalaxyMixin

T = TypeVar("T", bound="UploadItem")
TUploadContext = TypeVar("TUploadContext", bound="BaseUploadContext")

UploadMethodId = Literal[
    "local-file",
    "paste-content",
    "paste-links",
    "remote-files",
    "composite-file",
    "data-library",
    "explore-zip",
]

RuleImportContextId = Literal["rule"]
RuleImportTarget = Literal["datasets", "collections"]
RuleImportSource = Literal["pasted_table", "dataset_as_table", "remote_files", "workbook"]

CollectionType = Literal["list", "list:paired"]


class UploadMetadata(TypedDict, total=False):
    name: str
    extension: str
    dbkey: str
    deferred: bool


class UploadItem:
    def __init__(self, index: int, context: "_UploadStaging"):
        self.index = index
        self.context = context

    def set_name(self, name: str) -> "UploadItem":
        input_field = self.context._row_name_input(self.index).wait_for_visible()
        input_field.clear()
        input_field.send_keys(name)
        return self

    def set_extension(self, extension: str) -> "UploadItem":
        component = self.context._row_extension_select(self.index).wait_for_visible()
        self.context.driver_wrapper.select_set_value(component, extension)
        return self

    def set_dbkey(self, dbkey: str) -> "UploadItem":
        component = self.context._row_dbkey_select(self.index).wait_for_visible()
        self.context.driver_wrapper.select_set_value(component, dbkey)
        return self

    def set_deferred(self, deferred: bool) -> "UploadItem":
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
        if self.context._current_method_id != "paste-content":
            raise AssertionError("Per-item content editing is only available for the paste-content method")

        textarea_target = self.context.components.upload_activity.paste_content_row_textarea(
            row=self.context._row_number(self.index)
        )
        if textarea_target.is_absent or not textarea_target.is_displayed:
            self.context.components.upload_activity.paste_content_row_toggle_button(
                row=self.context._row_number(self.index)
            ).wait_for_and_click()
        textarea = textarea_target.wait_for_visible()
        textarea.clear()
        textarea.send_keys(content)
        return self

    def start(self) -> None:
        self.context.start()

    def remove(self) -> None:
        self.context._row_remove_button(self.index).wait_for_and_click()

    def to_list(self, name: str) -> "UploadItem":
        self.context.to_list(name)
        return self

    def to_paired_list(self, name: str) -> "UploadItem":
        self.context.to_paired_list(name)
        return self


class LocalUploadItem(UploadItem):
    def stage_local_file(self, test_path: str, metadata: UploadMetadata | None = None) -> "LocalUploadItem":
        return self.context.stage_local_file(test_path, metadata)


class PasteContentUploadItem(UploadItem):
    def stage_paste_content(self, content: str, metadata: UploadMetadata | None = None) -> "PasteContentUploadItem":
        return self.context.stage_paste_content(content, metadata)


class RemoteFileUploadItem(UploadItem):
    def stage_remote_file(
        self, source_label: str, file_label: str, metadata: UploadMetadata | None = None
    ) -> "RemoteFileUploadItem":
        return self.context.stage_remote_file(source_label, file_label, metadata)


class DataLibraryUploadItem(UploadItem):
    def stage_data_library_dataset(self, library_label: str, dataset_label: str) -> "DataLibraryUploadItem":
        return self.context.stage_data_library_dataset(library_label, dataset_label)


class _UploadStaging:
    """Shared base for upload staging state and row/item helpers.

    Common state and helpers used by both UploadContext (panel) and
    UploadMethodInlineContext (inline).  Subclasses provide the button
    group via _button_group and may override _pre_start for
    start-specific hooks.
    """

    def __init__(self, driver_wrapper: NavigatesGalaxyMixin):
        self.driver_wrapper = driver_wrapper
        self._item_count = 0
        self._current_method_id: UploadMethodId | None = None

    @property
    def components(self):
        """Access to component selectors."""
        return self.driver_wrapper.components

    def stage_local_file(self, test_path: str, metadata: UploadMetadata | None = None) -> LocalUploadItem:
        file_input = self.driver_wrapper.wait_for_selector("#local-file-input")
        if self.driver_wrapper.backend_type == "playwright":
            file_input.element_handle.set_input_files(test_path)
        else:
            file_input.send_keys(test_path)
        return self._create_item(LocalUploadItem, metadata)

    def stage_paste_content(self, content: str, metadata: UploadMetadata | None = None) -> PasteContentUploadItem:
        if self._item_count > 0:
            self.components.upload_activity.add_another_dataset_button.wait_for_and_click()

        row = self._row_number(self._item_count)
        textarea = self.components.upload_activity.paste_content_row_textarea(row=row).wait_for_visible()
        textarea.click()
        textarea.send_keys(content)

        return self._create_item(PasteContentUploadItem, metadata)

    def stage_remote_file(
        self, source_label: str, file_label: str, metadata: UploadMetadata | None = None
    ) -> RemoteFileUploadItem:
        raise NotImplementedError("stage_remote_file must be implemented by subclasses")

    def stage_data_library_dataset(self, library_label: str, dataset_label: str) -> DataLibraryUploadItem:
        raise NotImplementedError("stage_data_library_dataset must be implemented by subclasses")

    def stage_paste_link(self, url: str, metadata: UploadMetadata | None = None) -> UploadItem:
        textarea = self.components.upload_activity.paste_textarea.wait_for_visible()
        textarea.click()
        textarea.send_keys(url)
        self.components.upload_activity.add_urls_button.wait_for_and_click()

        return self._create_item(UploadItem, metadata)

    def stage_paste_links(self, url_metadata_pairs: list[tuple[str, UploadMetadata | None]]) -> "_UploadStaging":
        urls = [pair[0] for pair in url_metadata_pairs]
        textarea = self.components.upload_activity.paste_textarea.wait_for_visible()
        textarea.click()
        textarea.send_keys("\n".join(urls))
        self.components.upload_activity.add_urls_button.wait_for_and_click()

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

    def _create_item(self, item_class: type[T], metadata: UploadMetadata | None = None) -> T:
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

    def _row_number(self, index: int) -> int:
        return index + 1

    def _row_name_input(self, index: int):
        row = self._row_number(index)
        return self.components.upload_activity.row_name_input(row=row)

    def _row_extension_select(self, index: int):
        row = self._row_number(index)
        return self.components.upload_activity.row_extension_select(row=row)

    def _row_dbkey_select(self, index: int):
        row = self._row_number(index)
        return self.components.upload_activity.row_dbkey_select(row=row)

    def _select_method(self, method_id: UploadMethodId) -> None:
        if self._current_method_id == method_id:
            return
        self.components.upload_activity.method_card(method_id=method_id).wait_for_and_click()
        self._current_method_id = method_id

    @property
    def _button_group(self):
        raise NotImplementedError("Subclasses must provide _button_group")

    def _pre_start(self) -> None:
        pass

    def start(self) -> None:
        self._pre_start()
        self._button_group.start_button.wait_for_and_click()

    def cancel(self) -> None:
        self._button_group.cancel_button.wait_for_and_click()

    def _row_remove_button(self, index):
        raise AssertionError("Item removal is not available for this upload context")

    def _row_deferred_checkbox(self, index: int):
        raise AssertionError("Deferred option is not available for this upload context")

    def _row_deferred_label(self, index: int):
        raise AssertionError("Deferred label is not available for this upload context")

    def to_list(self, name: str) -> "_UploadStaging":
        raise AssertionError("Collection creation is not available for this upload context")

    def to_paired_list(self, name: str) -> "_UploadStaging":
        raise AssertionError("Collection creation is not available for this upload context")


class UploadContext(_UploadStaging):
    def __init__(self, method_id: UploadMethodId, driver_wrapper: NavigatesGalaxyMixin):
        self._collection_config: tuple[str, CollectionType] | None = None
        super().__init__(driver_wrapper)

        self._open_upload_activity(method_id)
        self._select_method(method_id)

    @property
    def _button_group(self):
        return self.components.upload_activity

    def _pre_start(self) -> None:
        self._apply_collection_config()

    def stage_remote_file(
        self, source_label: str, file_label: str, metadata: UploadMetadata | None = None
    ) -> RemoteFileUploadItem:
        if self._current_method_id != "remote-files":
            raise AssertionError("stage_remote_file is only available for the remote-files method")

        self.components.upload_activity.remote_files_browser_label(label=source_label).wait_for_and_click()
        self.components.upload_activity.remote_files_browser_label(label=file_label).wait_for_visible()
        self.components.upload_activity.remote_files_browser_label(label=file_label).wait_for_and_click()
        self.components.upload_activity.remote_files_add_selected.wait_for_and_click()
        return self._create_item(RemoteFileUploadItem, metadata)

    def stage_remote_files(
        self,
        source_label: str,
        file_labels: list[str],
        metadata_list: list[UploadMetadata | None] | None = None,
    ) -> list[RemoteFileUploadItem]:
        if self._current_method_id != "remote-files":
            raise AssertionError("stage_remote_files is only available for the remote-files method")

        if metadata_list is not None and len(metadata_list) != len(file_labels):
            raise AssertionError(
                f"metadata_list length ({len(metadata_list)}) must match file_labels length ({len(file_labels)})"
            )

        self.components.upload_activity.remote_files_browser_label(label=source_label).wait_for_and_click()

        for file_label in file_labels:
            self.components.upload_activity.remote_files_browser_label(label=file_label).wait_for_visible()
            self.components.upload_activity.remote_files_browser_label(label=file_label).wait_for_and_click()

        self.components.upload_activity.remote_files_add_selected.wait_for_and_click()

        items: list[RemoteFileUploadItem] = []
        for i in range(len(file_labels)):
            metadata = metadata_list[i] if metadata_list else None
            items.append(self._create_item(RemoteFileUploadItem, metadata))

        return items

    def stage_data_library_dataset(self, library_label: str, dataset_label: str) -> DataLibraryUploadItem:
        if self._current_method_id != "data-library":
            raise AssertionError("stage_data_library_dataset is only available for the data-library method")

        self.components.upload_activity.data_library_library_label(label=library_label).wait_for_and_click()
        self.components.upload_activity.data_library_item_label(label=dataset_label).wait_for_and_click()
        self.components.upload_activity.data_library_add_selected.wait_for_and_click()
        return self._create_item(DataLibraryUploadItem)

    def select_composite(self, composite_type: str) -> "UploadContext":
        if self._current_method_id != "composite-file":
            raise AssertionError("select_composite is only available for the composite-file method")

        self._select_composite_type(composite_type)
        return self

    def stage_composite_url_slot(self, slot: int, url: str) -> "UploadContext":
        if self._current_method_id != "composite-file":
            raise AssertionError("stage_composite_url_slot is only available for the composite-file method")
        if slot < 1:
            raise AssertionError("slot must be >= 1")

        self._select_composite_slot_mode(row=slot, mode="url")
        url_input = self.components.upload_activity.composite_slot_url_input(row=slot).wait_for_visible()
        url_input.clear()
        url_input.send_keys(url)
        return self

    def stage_composite_paste_slot(self, slot: int, content: str) -> "UploadContext":
        if self._current_method_id != "composite-file":
            raise AssertionError("stage_composite_paste_slot is only available for the composite-file method")
        if slot < 1:
            raise AssertionError("slot must be >= 1")

        self._select_composite_slot_mode(row=slot, mode="paste")
        paste_textarea = self.components.upload_activity.composite_slot_paste_textarea(row=slot).wait_for_visible()
        paste_textarea.clear()
        paste_textarea.send_keys(content)
        return self

    def stage_composite_file_slot(self, slot: int, file_path: str) -> "UploadContext":
        if self._current_method_id != "composite-file":
            raise AssertionError("stage_composite_file_slot is only available for the composite-file method")
        if slot < 1:
            raise AssertionError("slot must be >= 1")

        self._select_composite_slot_mode(row=slot, mode="local")
        file_input = self.components.upload_activity.composite_slot_file_input(row=slot).wait_for_present()
        if self.driver_wrapper.backend_type == "playwright":
            file_input.element_handle.set_input_files(file_path)
        else:
            file_input.send_keys(file_path)
        return self

    def _select_composite_type(self, composite_type: str) -> None:
        composite_type_lower = composite_type.lower()
        self.components.upload_activity.composite_type_enabled_dropdown.wait_for_and_click()

        visible_options = self.components.upload_activity.composite_type_options_visible.all()
        candidates: list[tuple[str, str]] = []
        for option in visible_options:
            option_id = option.get_attribute("data-id") or ""
            option_label = (option.get_attribute("data-label") or option.text or "").strip()
            if option_id:
                candidates.append((option_id, option_label))

        target_id: str | None = None
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

        self.components.upload_activity.composite_type_option_by_id_visible(id=target_id).wait_for_and_click()
        try:
            self.components.upload_activity.composite_first_slot.wait_for_visible(timeout=5)
        except Exception as exc:
            raise AssertionError(
                f"Composite slots did not render after selecting '{composite_type}'. Candidates: {candidates}"
            ) from exc

    def _select_composite_slot_mode(self, row: int, mode: Literal["local", "url", "paste"]) -> None:
        if mode == "local":
            visible_action_target = self.components.upload_activity.composite_slot_enter_local_action_visible
            input_target = self.components.upload_activity.composite_slot_file_input(row=row)
        elif mode == "url":
            visible_action_target = self.components.upload_activity.composite_slot_enter_url_action_visible
            input_target = self.components.upload_activity.composite_slot_url_input(row=row)
        else:
            visible_action_target = self.components.upload_activity.composite_slot_enter_paste_action_visible
            input_target = self.components.upload_activity.composite_slot_paste_textarea(row=row)

        for _ in range(2):
            dropdown = self.components.upload_activity.composite_slot_mode_dropdown(row=row).wait_for_visible()
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
        self.components.upload_activity.target_history_change_link.wait_for_and_click()
        self.components.upload_activity.history_selector_modal_item(history_id=history_id).wait_for_and_click()
        self.components.upload_activity.history_selector_modal.wait_for_absent_or_hidden()
        return self

    def to_list(self, name: str) -> "UploadContext":
        self._set_collection_config(name=name, collection_type="list")
        return self

    def to_paired_list(self, name: str) -> "UploadContext":
        self._set_collection_config(name=name, collection_type="list:paired")
        return self

    def _set_collection_config(self, name: str, collection_type: CollectionType) -> None:
        if not name.strip():
            raise AssertionError("Collection name is required")
        if self._current_method_id == "composite-file":
            raise AssertionError("Collection creation is not supported for the composite-file method")
        self._collection_config = (name.strip(), collection_type)

    def _apply_collection_config(self) -> None:
        if self._collection_config is None:
            return

        collection_name, collection_type = self._collection_config
        name_input_target = self.components.upload_activity.collection_name_input

        if name_input_target.is_absent or not name_input_target.is_displayed:
            self.components.upload_activity.collection_section.wait_for_and_click()

        name_input = name_input_target.wait_for_visible()
        name_input.clear()
        name_input.send_keys(collection_name)
        self.components.upload_activity.collection_type_select.wait_for_visible()
        self.components.upload_activity.collection_type_select.select_by_value(collection_type)

    def activate_advanced_mode(self) -> "UploadContext":
        return self.set_advanced_mode(True)

    def set_advanced_mode(self, enabled: bool) -> "UploadContext":
        checkbox = self.components.upload_activity.advanced_mode_toggle_checkbox.wait_for_present()
        if checkbox.is_selected() != enabled:
            self.driver_wrapper.execute_script("arguments[0].click();", checkbox)
        return self

    def toggle_advanced_mode(self) -> "UploadContext":
        checkbox = self.components.upload_activity.advanced_mode_toggle_checkbox.wait_for_present()
        self.driver_wrapper.execute_script("arguments[0].click();", checkbox)
        return self

    def select_target_object_store(self, object_store_id: str) -> "UploadContext":
        self.components.upload_activity.target_object_store_selector_dropdown.wait_for_and_click()
        self.components.upload_activity.target_object_store_selector_option(
            object_store_id=object_store_id
        ).wait_for_and_click()
        return self

    def _select_method(self, method_id: UploadMethodId) -> None:
        if self._current_method_id == method_id:
            return
        self.components.upload_activity.method_card(method_id=method_id).wait_for_and_click()
        self._current_method_id = method_id

    def _open_upload_activity(self, method_id: UploadMethodId) -> None:
        method_card = self.components.upload_activity.method_card(method_id=method_id)
        if not method_card.is_absent and method_card.is_displayed:
            return

        if (
            not self.components.upload_activity.activity.is_absent
            and self.components.upload_activity.activity.is_displayed
        ):
            self.components.upload_activity.activity.wait_for_and_click()
            if not method_card.is_absent and method_card.is_displayed:
                return

        self.driver_wrapper.home()
        self.driver_wrapper.components.tools.activity.wait_for_visible()

        if (
            not self.components.upload_activity.activity.is_absent
            and self.components.upload_activity.activity.is_displayed
        ):
            self.components.upload_activity.activity.wait_for_and_click()
            if not method_card.is_absent and method_card.is_displayed:
                return

        if (
            not self.driver_wrapper.components.preferences.activity.is_absent
            and self.driver_wrapper.components.preferences.activity.is_displayed
        ):
            self.driver_wrapper.components.preferences.activity.wait_for_and_click()
            self.components.upload_activity.activity.wait_for_and_click()

        method_card.wait_for_visible()

    def _row_remove_button(self, index):
        row = self._row_number(index)
        return self.components.upload_activity.row_remove_button(row=row)

    def _row_deferred_checkbox(self, index: int):
        if self._current_method_id != "paste-links":
            raise AssertionError("Deferred option is only available for the paste-links method")
        row = self._row_number(index)
        return self.components.upload_activity.paste_links_row_deferred_checkbox(row=row).wait_for_present()

    def _row_deferred_label(self, index: int):
        if self._current_method_id != "paste-links":
            raise AssertionError("Deferred label is only available for the paste-links method")
        row = self._row_number(index)
        return self.components.upload_activity.paste_links_row_deferred_label(row=row)


class UploadMethodInlineContext(_UploadStaging):
    """Inline upload context for workflow form inputs."""

    def __init__(self, method_id: UploadMethodId, driver_wrapper: NavigatesGalaxyMixin, label: str | None = None):
        self._label = label
        super().__init__(driver_wrapper)
        self._select_method(method_id)

    @property
    def _button_group(self):
        return self.components.upload_method_inline

    def _scoped_selector(self, child_selector: str) -> str:
        """Build a CSS selector scoped to the workflow input's data-label."""
        if self._label:
            return f'[data-label="{self._label}"] .upload-method-inline-content {child_selector}'
        return f".upload-method-inline-content {child_selector}"

    def _click_visible_element_with_selector(self, child_selector: str) -> None:
        """Find and click an element matching child_selector within the visible inline content.

        For collection inputs there may be multiple .upload-method-inline-content elements
        (one in .form-data and one in .tab-pane.active). This finds the one that is
        displayed and clicks the matching child within it.

        Falls back to selector-based lookup when no label is set.
        """
        if self._label is None:
            selector = self._scoped_selector(child_selector)
            self.driver_wrapper.wait_for_selector_clickable(selector)
            self.driver_wrapper.click_selector(selector)
            return

        container = self.driver_wrapper.find_element_by_selector(f'[data-label="{self._label}"]')
        contents = container.find_elements("css selector", ".upload-method-inline-content")
        if not contents:
            raise AssertionError(f"No inline upload content found for label '{self._label}'")

        # Pick the displayed one; fall back to first if none are displayed.
        target = next((el for el in contents if el.is_displayed()), contents[0])

        try:
            element = target.find_element("css selector", child_selector)
        except Exception:
            raise AssertionError(
                f"Could not find '{child_selector}' in visible inline content for label '{self._label}'"
            )

        element.click()

    def _select_method(self, method_id: UploadMethodId) -> None:
        if self._current_method_id == method_id:
            return
        self._click_visible_element_with_selector(f'[data-method-id="{method_id}"]')
        self._current_method_id = method_id

    def start(self) -> None:
        self._pre_start()
        self._click_visible_element_with_selector('[data-test-id="upload-method-inline-start"]')

    def cancel(self) -> None:
        self._click_visible_element_with_selector('[data-test-id="upload-method-inline-cancel"]')


# Mode-specific context classes that provide restricted APIs
class BaseUploadContext:
    def __init__(self, context: UploadContext):
        self._context = context

    def start(self) -> None:
        self._context.start()

    def cancel(self) -> None:
        self._context.cancel()

    def select_target_history(self: TUploadContext, history_id: str) -> TUploadContext:
        self._context.select_target_history(history_id)
        return self

    def to_list(self, name: str) -> "BaseUploadContext":
        self._context.to_list(name)
        return self

    def to_paired_list(self, name: str) -> "BaseUploadContext":
        self._context.to_paired_list(name)
        return self

    def _start_and_wait_for_uploaded_hids(self) -> list[int]:
        staged_item_count = self._context._item_count
        if staged_item_count < 1:
            raise AssertionError("No staged upload items found. Stage files/content before creating collections.")

        initial_hid = self._current_latest_hid() + 1
        self._context.start()
        last_hid = initial_hid + staged_item_count - 1
        uploaded_hids = list(range(initial_hid, last_hid + 1))
        for hid in uploaded_hids:
            self._context.driver_wrapper.history_panel_wait_for_hid_ok(hid)
        return uploaded_hids

    def _current_latest_hid(self) -> int:
        latest_item = self._context.driver_wrapper._latest_history_item()
        if latest_item and isinstance(latest_item, dict) and "hid" in latest_item:
            return int(latest_item["hid"])
        return 0

    def activate_advanced_mode(self: TUploadContext) -> TUploadContext:
        self._context.activate_advanced_mode()
        return self

    def set_advanced_mode(self: TUploadContext, enabled: bool) -> TUploadContext:
        self._context.set_advanced_mode(enabled)
        return self

    def toggle_advanced_mode(self: TUploadContext) -> TUploadContext:
        self._context.toggle_advanced_mode()
        return self

    def select_target_object_store(self: TUploadContext, object_store_id: str) -> TUploadContext:
        self._context.select_target_object_store(object_store_id)
        return self


class LocalFileContext(BaseUploadContext):
    def stage_local_file(self, test_path: str, metadata: UploadMetadata | None = None) -> LocalUploadItem:
        return self._context.stage_local_file(test_path, metadata)


class PasteContentContext(BaseUploadContext):
    def stage_paste_content(self, content: str, metadata: UploadMetadata | None = None) -> PasteContentUploadItem:
        return self._context.stage_paste_content(content, metadata)


class PasteLinksContext(BaseUploadContext):
    def stage_paste_link(self, url: str, metadata: UploadMetadata | None = None) -> UploadItem:
        return self._context.stage_paste_link(url, metadata)

    def stage_paste_links(self, url_metadata_pairs: list[tuple[str, UploadMetadata | None]]) -> "PasteLinksContext":
        self._context.stage_paste_links(url_metadata_pairs)
        return self


class RemoteFilesContext(BaseUploadContext):
    def stage_remote_file(
        self, source_label: str, file_label: str, metadata: UploadMetadata | None = None
    ) -> RemoteFileUploadItem:
        return self._context.stage_remote_file(source_label, file_label, metadata)

    def stage_remote_files(
        self,
        source_label: str,
        file_labels: list[str],
        metadata_list: list[UploadMetadata | None] | None = None,
    ) -> "RemoteFilesContext":
        self._context.stage_remote_files(source_label, file_labels, metadata_list)
        return self


class CompositeFileContext(BaseUploadContext):
    def select_composite(self, composite_type: str) -> "CompositeFileContext":
        self._context.select_composite(composite_type)
        return self

    def stage_composite_url_slot(self, slot: int, url: str) -> "CompositeFileContext":
        self._context.stage_composite_url_slot(slot, url)
        return self

    def stage_composite_paste_slot(self, slot: int, content: str) -> "CompositeFileContext":
        self._context.stage_composite_paste_slot(slot, content)
        return self

    def stage_composite_file_slot(self, slot: int, file_path: str) -> "CompositeFileContext":
        self._context.stage_composite_file_slot(slot, file_path)
        return self


class DataLibraryContext(BaseUploadContext):
    def stage_data_library_dataset(self, library_label: str, dataset_label: str) -> DataLibraryUploadItem:
        return self._context.stage_data_library_dataset(library_label, dataset_label)


class ExploreZipContext(BaseUploadContext):
    @property
    def _wizard(self):
        return self._context.driver_wrapper.components.zip_import_wizard

    def explore_local_zip(self, test_path: str) -> "ExploreZipContext":
        file_input = self._wizard.local_file_input.wait_for_present()
        if self._context.driver_wrapper.backend_type == "playwright":
            file_input.element_handle.set_input_files(test_path)
        else:
            file_input.send_keys(test_path)
        return self

    def explore_remote_zip(self, url: str) -> "ExploreZipContext":
        url_input = self._wizard.remote_url_input.wait_for_visible()
        self._context.driver_wrapper.set_element_value(url_input, url)
        return self

    def go_next(self) -> "ExploreZipContext":
        self._wizard.wizard_next_button.wait_for_and_click()
        return self

    def start_import(self) -> "ExploreZipContext":
        self._wizard.wizard_import_button.wait_for_and_click()
        return self

    def select_file(self, file_path: str) -> "ExploreZipContext":
        self._wizard.select_file(file_path=file_path).wait_for_and_click()
        return self

    def select_all_files(self) -> "ExploreZipContext":
        self._wizard.select_all_checkbox.wait_for_and_click()
        return self

    def search_for(self, query: str) -> "ExploreZipContext":
        search_input = self._wizard.search_input.wait_for_visible()
        search_input.send_keys(query)
        self._context.driver_wrapper.sleep_for(self._context.driver_wrapper.wait_types.UX_RENDER)
        return self

    def get_visible_item_cards(self) -> list:
        return self._context.driver_wrapper.find_elements_by_selector(".zip-file-selector .g-card")

    def wait_for_preview(self) -> "ExploreZipContext":
        loading_indicator = self._wizard.loading_indicator
        loading_indicator.wait_for_present()
        loading_indicator.wait_for_absent()
        return self

    def expect_total_files(self, count: int) -> "ExploreZipContext":
        badge_text = self._wizard.zip_file_count_badge.wait_for_text()
        assert badge_text.startswith(f"{count}"), f"Expected {count} files but badge says: {badge_text}"
        return self

    def expect_files_to_import(self, count: int) -> "ExploreZipContext":
        badge_text = self._wizard.selected_files_to_import_count_badge.wait_for_text()
        assert badge_text.startswith(f"{count}"), f"Expected {count} files to import but badge says: {badge_text}"
        return self

    def expect_workflows_to_import(self, count: int) -> "ExploreZipContext":
        badge_text = self._wizard.selected_workflows_to_import_count_badge.wait_for_text()
        assert badge_text.startswith(f"{count}"), f"Expected {count} workflows to import but badge says: {badge_text}"
        return self

    def expect_preview_title(self, title: str) -> "ExploreZipContext":
        title_text = self._wizard.preview_title.wait_for_text()
        assert title_text == title, f"Expected preview title '{title}' but got '{title_text}'"
        return self


class RuleImportContext:
    def __init__(self, driver_wrapper: NavigatesGalaxyMixin):
        self.driver_wrapper = driver_wrapper
        self.driver_wrapper.get("rules")
        self.driver_wrapper.components.file_set_wizard.creating_what_datasets.wait_for_visible()

    @property
    def components(self):
        return self.driver_wrapper.components

    def creating(self, creating_what: RuleImportTarget) -> "RuleImportContext":
        wizard = self.components.file_set_wizard
        if creating_what == "datasets":
            wizard.creating_what_datasets.wait_for_and_click()
        else:
            wizard.creating_what_collections.wait_for_and_click()
        wizard.wizard_next_button.wait_for_and_click()
        return self

    def from_source(self, source: RuleImportSource) -> "RuleImportContext":
        wizard = self.components.file_set_wizard
        source_map = {
            "pasted_table": wizard.source_pasted_table,
            "dataset_as_table": wizard.source_dataset_as_table,
            "remote_files": wizard.source_remote_files,
            "workbook": wizard.source_workbook,
        }
        source_map[source].wait_for_and_click()
        wizard.wizard_next_button.wait_for_and_click()
        return self

    def paste_content(self, content: str) -> "RuleImportContext":
        wizard = self.components.file_set_wizard
        wizard.paste_textarea.wait_for_and_send_keys(content)
        wizard.wizard_next_button.wait_for_and_click()
        return self.wait_for_builder()

    def wait_for_dataset_dialog(self) -> "RuleImportContext":
        self.driver_wrapper.wait_for_selector_visible(".selection-dialog-modal")
        return self

    def select_dataset(self, row: int = 1) -> "RuleImportContext":
        self.wait_for_dataset_dialog()
        self.driver_wrapper.wait_for_and_click_selector(
            f'.selection-dialog-modal table tbody tr[aria-rowindex="{row}"] td[aria-colindex="1"]'
        )
        self.driver_wrapper.wait_for_selector_absent_or_hidden(".selection-dialog-modal")
        wizard = self.components.file_set_wizard
        wizard.wizard_next_button.wait_for_and_click()
        return self.wait_for_builder()

    def wait_for_builder(self) -> "RuleImportContext":
        self.components.rule_builder.menu_button_filter.wait_for_visible()
        return self


# Mapping of upload method IDs to their corresponding context classes
_CONTEXT_CLASS_MAP: dict[UploadMethodId, type[BaseUploadContext]] = {
    "local-file": LocalFileContext,
    "paste-content": PasteContentContext,
    "paste-links": PasteLinksContext,
    "remote-files": RemoteFilesContext,
    "composite-file": CompositeFileContext,
    "data-library": DataLibraryContext,
    "explore-zip": ExploreZipContext,
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

    @overload
    def upload_context(self, method_id: Literal["explore-zip"]) -> ExploreZipContext: ...

    @overload
    def upload_context(self, method_id: RuleImportContextId) -> RuleImportContext: ...

    def upload_context(
        self, method_id: UploadMethodId | RuleImportContextId
    ) -> (
        LocalFileContext
        | PasteContentContext
        | PasteLinksContext
        | RemoteFilesContext
        | CompositeFileContext
        | DataLibraryContext
        | ExploreZipContext
        | RuleImportContext
    ):
        if method_id == "rule":
            return RuleImportContext(self)

        base_context = UploadContext(method_id, self)
        context_class = _CONTEXT_CLASS_MAP[method_id]
        return context_class(base_context)  # type: ignore[return-value]

    def _rule_import_context(self) -> RuleImportContext:
        context = getattr(self, "_active_rule_import_context", None)
        if context is None:
            context = self.upload_context("rule")
            self._active_rule_import_context = context
        return context

    def upload_inline(self, method_id: UploadMethodId, label: str | None = None) -> UploadMethodInlineContext:
        """Upload context for inline upload methods (used in workflow form inputs).

        Args:
            method_id: The upload method to use (e.g., "paste-content").
            label: Optional workflow input label to scope the inline upload to.
                Required when multiple inputs have visible inline upload views.
        """
        return UploadMethodInlineContext(method_id, self, label=label)
