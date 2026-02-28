<script setup lang="ts">
import { faCheck, faCloud, faEdit, faExclamation, faLaptop, faLink, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem, BFormInput, BFormTextarea } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { useFileDrop } from "@/composables/fileDrop";
import { validateUrl } from "@/utils/url";
import { bytesToString } from "@/utils/utils";

import type { CompositeSlot, CompositeSlotMode } from "../types/uploadItem";

import GButton from "@/components/BaseComponents/GButton.vue";
import RemoteFileBrowserModal from "@/components/FileBrowser/RemoteFileBrowserModal.vue";

interface Props {
    slotItem: CompositeSlot;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:slotItem", updated: CompositeSlot): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const dropZoneRef = ref<HTMLElement | null>(null);
const showRemoteBrowser = ref(false);

const urlValidation = computed(() => {
    if (props.slotItem.mode !== "url") {
        return null;
    }
    const url = props.slotItem.url.trim();
    if (!url) {
        return null;
    }
    return validateUrl(url);
});

const urlInputState = computed(() => urlValidation.value?.isValid ?? null);
const urlValidationMessage = computed(() => urlValidation.value?.message ?? null);

const isFilled = computed(() => {
    const slotItem = props.slotItem;
    if (slotItem.mode === "local") {
        return !!slotItem.file;
    }
    if (slotItem.mode === "url") {
        return !!slotItem.url.trim() && validateUrl(slotItem.url.trim()).isValid;
    }
    if (slotItem.mode === "remote") {
        return !!slotItem.remoteUri;
    }
    return !!slotItem.content.trim();
});

const dropdownLabel = computed(() => {
    const slotItem = props.slotItem;
    if (slotItem.mode === "local" && slotItem.file) {
        return "Local File";
    }
    if (slotItem.mode === "url") {
        return "URL";
    }
    if (slotItem.mode === "paste") {
        return "Paste";
    }
    if (slotItem.mode === "remote") {
        return "Remote File";
    }
    return "Select";
});

/** Extracts the shared base fields from the current slot to build a fresh typed variant */
function base() {
    const { slotName, description, optional } = props.slotItem;
    return { slotName, description, optional };
}

function openFileBrowser() {
    fileInputRef.value?.click();
}

function selectMode(mode: CompositeSlotMode) {
    if (mode === "local") {
        emit("update:slotItem", { ...base(), mode: "local", fileSize: 0 });
    } else if (mode === "url") {
        emit("update:slotItem", { ...base(), mode: "url", url: "" });
    } else if (mode === "paste") {
        emit("update:slotItem", { ...base(), mode: "paste", content: "" });
    } else {
        emit("update:slotItem", { ...base(), mode: "remote", remoteUri: "", remoteName: "", fileSize: 0 });
    }
}

function onFileSelected(files: FileList | null) {
    const file = files?.[0] ?? null;
    if (file) {
        emit("update:slotItem", { ...base(), mode: "local", file, fileSize: file.size });
    }
    // Reset input so the same file can be re-selected if cleared
    if (fileInputRef.value) {
        fileInputRef.value.value = "";
    }
}

function onFileInputChange(event: Event) {
    const target = event.target as HTMLInputElement | null;
    onFileSelected(target?.files ?? null);
}

function onDrop(evt: DragEvent) {
    const file = evt.dataTransfer?.files?.[0];
    if (file) {
        emit("update:slotItem", { ...base(), mode: "local", file, fileSize: file.size });
    }
}

const { isFileOverDropZone } = useFileDrop({
    dropZone: dropZoneRef,
    onDrop: () => {},
    onDropCancel: () => {},
    solo: false,
    ignoreChildrenOnLeave: true,
});

function clearSlot() {
    emit("update:slotItem", { ...base(), mode: "local", fileSize: 0 });
}

function onRemoteFileSelected(items: SelectionItem[]) {
    const item = items[0];
    if (item) {
        const fileSize = (item.entry as { size?: number }).size ?? 0;
        emit("update:slotItem", { ...base(), mode: "remote", remoteUri: item.url, remoteName: item.label, fileSize });
    }
    showRemoteBrowser.value = false;
}

function onUrlInput(value: string) {
    emit("update:slotItem", { ...base(), mode: "url", url: value });
}

function onPasteInput(value: string) {
    emit("update:slotItem", { ...base(), mode: "paste", content: value });
}

const display = computed(() => {
    const slotItem = props.slotItem;
    const isLocal = slotItem.mode === "local";
    const isRemote = slotItem.mode === "remote";
    const isPaste = slotItem.mode === "paste";
    return {
        fileSize: isLocal || isRemote ? slotItem.fileSize : isPaste ? new Blob([slotItem.content]).size : 0,
        localFileName: isLocal ? slotItem.file?.name : undefined,
        urlValue: slotItem.mode === "url" ? slotItem.url : "",
        pasteContent: slotItem.mode === "paste" ? slotItem.content : "",
        remoteName: isRemote ? slotItem.remoteName || slotItem.remoteUri : "",
        hasRemoteFile: isRemote && !!slotItem.remoteUri,
    };
});
</script>

<template>
    <div
        ref="dropZoneRef"
        class="composite-slot-row rounded border p-2 mb-2"
        :class="{
            'slot-dragging': isFileOverDropZone,
            'slot-filled': isFilled,
            'slot-required-empty': !isFilled && !slotItem.optional,
        }"
        data-galaxy-file-drop-target
        role="button"
        tabindex="0"
        :aria-label="`Upload slot for ${slotItem.description}`"
        @dragover.prevent
        @drop.prevent="onDrop">
        <!-- Main row -->
        <div class="d-flex align-items-center">
            <!-- Status icon -->
            <div class="slot-status-icon flex-shrink-0 mr-2">
                <FontAwesomeIcon
                    v-if="isFilled"
                    v-g-tooltip.hover.noninteractive
                    :icon="faCheck"
                    class="text-success"
                    title="Slot filled"
                    fixed-width />
                <FontAwesomeIcon
                    v-else-if="slotItem.optional"
                    v-g-tooltip.hover.noninteractive
                    :icon="faCheck"
                    class="text-info"
                    title="Optional — can be left empty"
                    fixed-width />
                <FontAwesomeIcon
                    v-else
                    v-g-tooltip.hover.noninteractive
                    :icon="faExclamation"
                    class="text-warning"
                    title="Required — must be filled before upload"
                    fixed-width />
            </div>

            <!-- Slot description -->
            <div class="slot-description flex-grow-1 mr-2">
                <span class="font-weight-bold text-truncate">{{ slotItem.description }}</span>
                <small v-if="slotItem.optional" class="text-muted ml-1">(optional)</small>
            </div>

            <!-- File size badge -->
            <small v-if="display.fileSize > 0" class="text-muted mr-2 flex-shrink-0">
                {{ bytesToString(display.fileSize) }}
            </small>

            <!-- Source mode dropdown -->
            <BDropdown size="sm" :variant="isFilled ? 'secondary' : 'primary'" class="mr-1 flex-shrink-0">
                <template v-slot:button-content>
                    {{ dropdownLabel }}
                </template>
                <BDropdownItem @click="openFileBrowser">
                    <FontAwesomeIcon :icon="faLaptop" fixed-width class="mr-1" />
                    Choose local file
                </BDropdownItem>
                <BDropdownItem @click="showRemoteBrowser = true">
                    <FontAwesomeIcon :icon="faCloud" fixed-width class="mr-1" />
                    Browse remote files
                </BDropdownItem>
                <BDropdownItem @click="selectMode('url')">
                    <FontAwesomeIcon :icon="faLink" fixed-width class="mr-1" />
                    Enter URL
                </BDropdownItem>
                <BDropdownItem @click="selectMode('paste')">
                    <FontAwesomeIcon :icon="faEdit" fixed-width class="mr-1" />
                    Paste content
                </BDropdownItem>
            </BDropdown>

            <!-- Clear button -->
            <GButton
                v-if="isFilled"
                size="small"
                transparent
                icon-only
                tooltip
                title="Clear this slot"
                class="flex-shrink-0"
                @click="clearSlot">
                <FontAwesomeIcon :icon="faTimes" fixed-width />
            </GButton>
            <!-- Spacer to keep layout stable when no clear button -->
            <span v-else class="slot-clear-placeholder" />
        </div>

        <!-- Local file info row -->
        <div v-if="display.localFileName" class="mt-2">
            <BFormInput :value="display.localFileName" readonly class="slot-file-name-input font-monospace" />
        </div>

        <!-- URL input row -->
        <div v-if="slotItem.mode === 'url'" class="mt-2">
            <BFormInput
                :value="display.urlValue"
                size="sm"
                placeholder="https://example.com/file.ext"
                class="slot-url-input font-monospace"
                :state="urlInputState"
                @input="onUrlInput" />
            <small v-if="urlValidationMessage" class="text-danger">
                {{ urlValidationMessage }}
            </small>
        </div>

        <!-- Paste content textarea -->
        <div v-if="slotItem.mode === 'paste'" class="mt-2">
            <BFormTextarea
                :value="display.pasteContent"
                rows="3"
                size="sm"
                placeholder="Paste file content here"
                @input="onPasteInput" />
        </div>

        <!-- Remote file display row -->
        <div v-if="display.hasRemoteFile" class="mt-2">
            <BFormInput :value="display.remoteName" readonly class="slot-file-name-input font-monospace" />
        </div>
        <div v-else-if="slotItem.mode === 'remote'" class="mt-2 text-muted small">
            No file selected — click the dropdown to browse remote sources.
        </div>

        <!-- Hidden file input -->
        <input ref="fileInputRef" type="file" class="d-none" @change="onFileInputChange" />

        <!-- Remote file browser modal -->
        <RemoteFileBrowserModal
            :show.sync="showRemoteBrowser"
            title="Browse Remote Files"
            mode="file"
            :multiple="false"
            ok-text="Select File"
            @select="onRemoteFileSelected" />
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.composite-slot-row {
    background-color: $gray-100;
    transition:
        background-color 0.15s ease,
        border-color 0.15s ease;
    border-color: $border-color !important;

    &.slot-dragging {
        background-color: lighten($brand-primary, 55%);
        border-color: $brand-primary !important;
    }

    &.slot-filled {
        border-color: lighten($brand-success, 20%) !important;
    }

    &.slot-required-empty {
        border-color: lighten($brand-warning, 10%) !important;
    }
}

.slot-description {
    min-width: 0; // allow text-truncate to work inside flex
    overflow: hidden;
}

.slot-url-input {
    font-size: 0.85rem;
}

.slot-clear-placeholder {
    display: inline-block;
    width: 1.4em; // same width as the clear button + margin to prevent layout shift
}

.slot-status-icon {
    width: 1.2em;
    text-align: center;
}
</style>
