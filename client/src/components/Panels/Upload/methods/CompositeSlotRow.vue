<script setup lang="ts">
import { faCheck, faEdit, faExclamation, faLaptop, faLink, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem, BFormInput, BFormTextarea } from "bootstrap-vue";
import { computed, ref } from "vue";

import { bytesToString } from "@/utils/utils";

import type { CompositeSlot, CompositeSlotMode } from "../types/uploadItem";

interface Props {
    slotItem: CompositeSlot;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:slotItem", updated: CompositeSlot): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);

const isFilled = computed(() => {
    const slotItem = props.slotItem;
    if (slotItem.mode === "local") {
        return !!slotItem.file;
    }
    if (slotItem.mode === "url") {
        return !!slotItem.url.trim();
    }
    return !!slotItem.content.trim();
});

const dropdownLabel = computed(() => {
    const slotItem = props.slotItem;
    if (slotItem.mode === "local" && slotItem.file) {
        const name = slotItem.file.name;
        return name.length > 24 ? `${name.slice(0, 22)}…` : name;
    }
    if (slotItem.mode === "url") {
        return "URL";
    }
    if (slotItem.mode === "paste") {
        return "Paste";
    }
    return "Select";
});

function update(patch: Partial<CompositeSlot>) {
    emit("update:slotItem", { ...props.slotItem, ...patch });
}

function openFileBrowser() {
    fileInputRef.value?.click();
}

function selectMode(mode: CompositeSlotMode) {
    update({ mode, file: undefined, fileSize: 0, url: "", content: "" });
}

function onFileSelected(files: FileList | null) {
    const file = files?.[0] ?? null;
    if (file) {
        update({ mode: "local", file, fileSize: file.size });
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
    isDragging.value = false;
    const file = evt.dataTransfer?.files?.[0];
    if (file) {
        update({ mode: "local", file, fileSize: file.size });
    }
}

function clearSlot() {
    update({ mode: "local", file: undefined, fileSize: 0, url: "", content: "" });
}
</script>

<template>
    <div
        class="composite-slot-row rounded border p-2 mb-2"
        :class="{
            'slot-dragging': isDragging,
            'slot-filled': isFilled,
            'slot-required-empty': !isFilled && !slotItem.optional,
        }"
        role="button"
        tabindex="0"
        :aria-label="`Upload slot for ${slotItem.description}`"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
        @keydown.enter.prevent="openFileBrowser"
        @keydown.space.prevent="openFileBrowser">
        <!-- Main row -->
        <div class="d-flex align-items-center">
            <!-- Status icon -->
            <div class="slot-status-icon flex-shrink-0 mr-2">
                <FontAwesomeIcon
                    v-if="isFilled"
                    v-b-tooltip.hover.noninteractive
                    :icon="faCheck"
                    class="text-success"
                    title="Slot filled"
                    fixed-width />
                <FontAwesomeIcon
                    v-else-if="slotItem.optional"
                    v-b-tooltip.hover.noninteractive
                    :icon="faCheck"
                    class="text-info"
                    title="Optional — can be left empty"
                    fixed-width />
                <FontAwesomeIcon
                    v-else
                    v-b-tooltip.hover.noninteractive
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
            <small v-if="slotItem.fileSize > 0" class="text-muted mr-2 flex-shrink-0">
                {{ bytesToString(slotItem.fileSize) }}
            </small>

            <!-- Source mode dropdown -->
            <BDropdown size="sm" :variant="isFilled ? 'outline-secondary' : 'primary'" class="mr-1 flex-shrink-0">
                <template v-slot:button-content>
                    {{ dropdownLabel }}
                </template>
                <BDropdownItem @click="openFileBrowser">
                    <FontAwesomeIcon :icon="faLaptop" fixed-width class="mr-1" />
                    Choose local file
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
            <button
                v-if="isFilled"
                v-b-tooltip.hover.noninteractive
                class="btn btn-sm btn-link text-muted p-0 flex-shrink-0"
                title="Clear this slot"
                @click="clearSlot">
                <FontAwesomeIcon :icon="faTimes" fixed-width />
            </button>
            <!-- Spacer to keep layout stable when no clear button -->
            <span v-else class="slot-clear-placeholder" />
        </div>

        <!-- URL input row -->
        <div v-if="slotItem.mode === 'url'" class="mt-2">
            <BFormInput
                :value="slotItem.url"
                size="sm"
                placeholder="https://example.com/file.ext"
                class="slot-url-input font-monospace"
                @input="update({ url: $event })" />
        </div>

        <!-- Paste content textarea -->
        <div v-if="slotItem.mode === 'paste'" class="mt-2">
            <BFormTextarea
                :value="slotItem.content"
                rows="3"
                size="sm"
                placeholder="Paste file content here"
                @input="update({ content: $event })" />
        </div>

        <!-- Hidden file input -->
        <input ref="fileInputRef" type="file" class="d-none" @change="onFileInputChange" />
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
