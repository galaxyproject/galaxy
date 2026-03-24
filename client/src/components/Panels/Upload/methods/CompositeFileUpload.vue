<script setup lang="ts">
import { faLayerGroup } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadStaging } from "@/composables/upload/useUploadStaging";
import type { ExtensionDetails } from "@/composables/uploadConfigurations";
import {
    buildPreparedUploadWithOptions,
    createFileUploadItem,
    createPastedUploadItem,
    createUrlUploadItem,
} from "@/utils/upload";
import { mapToCompositeFileUpload } from "@/utils/upload/itemMappers";

import type { PreparedUpload, UploadMethodComponent, UploadMethodConfig } from "../types";
import type { CompositeFileItem, CompositeSlot } from "../types/uploadItem";

import UploadTableDbKeyCell from "../shared/UploadTableDbKeyCell.vue";
import CompositeSlotRow from "./CompositeSlotRow.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import SingleItemSelector from "@/components/SingleItemSelector.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const { compositeExtensions, listDbKeys, configurationsReady, defaultDbKey } = useUploadDefaults();

const compositeItems = ref<CompositeFileItem[]>([]);
const { clear: clearStaging } = useUploadStaging<CompositeFileItem>(props.method.id, compositeItems);

const currentItem = computed((): CompositeFileItem | null => compositeItems.value[0] ?? null);

const selectedExtension = computed((): string => currentItem.value?.extension ?? "");

const defaultNullSelection: ExtensionDetails = {
    id: "",
    text: "— Select composite type —",
    description: null,
    description_url: null,
    composite_files: null,
};

const availableExtensions = computed(() => [defaultNullSelection, ...compositeExtensions.value]);

const slots = computed((): CompositeSlot[] => currentItem.value?.slots ?? []);

const selectedExtensionDetails = computed(
    () => availableExtensions.value.find((ext) => ext.id === selectedExtension.value) ?? null,
);

const hasAllRequiredSlots = computed((): boolean => {
    if (!currentItem.value) {
        return false;
    }
    return slots.value.every((slot) => {
        if (slot.optional) {
            return true;
        }
        if (slot.mode === "local") {
            return !!slot.file;
        }
        if (slot.mode === "url") {
            return !!slot.url.trim();
        }
        if (slot.mode === "remote") {
            return !!slot.remoteUri;
        }
        return !!slot.content.trim();
    });
});

const isReadyToUpload = computed((): boolean => !!currentItem.value && hasAllRequiredSlots.value);

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

function updateItem(patch: Partial<CompositeFileItem>) {
    if (!currentItem.value) {
        return;
    }
    compositeItems.value = [{ ...currentItem.value, ...patch }];
}

function updateSlot(index: number, updated: CompositeSlot) {
    if (!currentItem.value) {
        return;
    }
    const newSlots = [...currentItem.value.slots];
    newSlots[index] = updated;
    compositeItems.value = [{ ...currentItem.value, slots: newSlots }];
}

/** Called when the user picks a new composite type from the dropdown. */
function onExtensionChange(newExtension: string) {
    if (!newExtension) {
        compositeItems.value = [];
        return;
    }

    const extDetails = availableExtensions.value.find((e) => e.id === newExtension);
    if (!extDetails?.composite_files) {
        compositeItems.value = [];
        return;
    }

    // Preserve dataset name and dbkey if the user already set them
    const existingItem = currentItem.value;

    compositeItems.value = [
        {
            name: existingItem?.name ?? "",
            extension: newExtension,
            dbkey: existingItem?.dbkey ?? defaultDbKey.value,
            slots: extDetails.composite_files.map(
                (compositeFile): CompositeSlot => ({
                    slotName: compositeFile.name,
                    description: compositeFile.description ?? compositeFile.name,
                    optional: compositeFile.optional,
                    mode: "local",
                    fileSize: 0,
                }),
            ),
        },
    ];
}

function onDatasetNameInput(name: string | null) {
    updateItem({ name: name ?? "" });
}

function onDbKeyInput(dbkey: string | null) {
    if (dbkey !== null) {
        updateItem({ dbkey });
    }
}

function clearAll() {
    compositeItems.value = [];
    clearStaging();
}

function prepareUpload(): PreparedUpload | null {
    const item = currentItem.value;
    if (!item) {
        return null;
    }

    const uploadItem = mapToCompositeFileUpload(item, props.targetHistoryId);
    const baseOptions = {
        dbkey: uploadItem.dbkey,
        ext: uploadItem.extension,
        space_to_tab: uploadItem.spaceToTab,
        to_posix_lines: uploadItem.toPosixLines,
        deferred: false,
    };

    const apiItems = uploadItem.slots
        .filter((slot) => slot.src !== "files" || !!slot.file)
        .map((slot) => {
            const slotOptions = {
                name: slot.slotName,
                ...baseOptions,
            };

            if (slot.src === "files") {
                return createFileUploadItem(slot.file!, uploadItem.targetHistoryId, {
                    ...slotOptions,
                    size: slot.fileSize ?? slot.file!.size,
                });
            }

            if (slot.src === "url") {
                return createUrlUploadItem(slot.url ?? "", uploadItem.targetHistoryId, {
                    ...slotOptions,
                    size: slot.fileSize ?? 0,
                });
            }

            return createPastedUploadItem(slot.content ?? "", uploadItem.targetHistoryId, {
                ...slotOptions,
                size: slot.fileSize ?? (slot.content ?? "").length,
            });
        });

    if (apiItems.length === 0) {
        return null;
    }

    return buildPreparedUploadWithOptions([uploadItem], undefined, {
        apiItems,
        uploadOptions: {
            composite: true,
            compositeName: uploadItem.name,
        },
    });
}

function reset() {
    compositeItems.value = [];
    clearStaging();
}

defineExpose<UploadMethodComponent>({ prepareUpload, reset });
</script>

<template>
    <div class="composite-file-upload">
        <div class="composite-config-panel mb-3">
            <div class="d-flex flex-wrap flex-gapx-1 flex-gapy-1 align-items-start">
                <!-- Composite type selector -->
                <div class="composite-config-field d-flex flex-column">
                    <label class="font-weight-bold mb-1" for="composite-type-selector"> Composite Type </label>
                    <SingleItemSelector
                        id="composite-type-selector"
                        v-b-tooltip.hover.noninteractive
                        collection-name="Composite Types"
                        title="Composite Type"
                        :items="availableExtensions"
                        :current-item="availableExtensions.find((ext) => ext.id === selectedExtension)"
                        :disabled="!configurationsReady"
                        @update:selected-item="(ext) => onExtensionChange(ext?.id ?? '')" />
                </div>

                <!-- Dataset name -->
                <div class="composite-config-field d-flex flex-column">
                    <label for="composite-dataset-name" class="font-weight-bold mb-1">
                        Dataset Name
                        <small class="text-muted ml-1">(optional)</small>
                    </label>
                    <GFormInput
                        id="composite-dataset-name"
                        class="form-control"
                        :value="currentItem?.name ?? ''"
                        :disabled="!currentItem"
                        placeholder="Provide a name for the dataset"
                        @input="onDatasetNameInput" />
                </div>

                <!-- DB key / Reference -->
                <div class="composite-config-field d-flex flex-column">
                    <label class="font-weight-bold mb-1 d-block" for="composite-dbkey">
                        Reference
                        <small class="text-muted ml-1">(optional)</small>
                    </label>
                    <UploadTableDbKeyCell
                        id="composite-dbkey"
                        :value="currentItem?.dbkey ?? defaultDbKey"
                        :db-keys="listDbKeys"
                        :disabled="!configurationsReady || !currentItem"
                        @input="onDbKeyInput" />
                </div>
            </div>

            <!-- Composite type description -->
            <div
                v-if="selectedExtensionDetails?.description || selectedExtensionDetails?.description_url"
                class="text-muted mt-2">
                <div v-if="selectedExtensionDetails?.description" class="mb-1">
                    {{ selectedExtensionDetails.description }}
                </div>
                <div v-if="selectedExtensionDetails?.description_url">
                    <ExternalLink :href="selectedExtensionDetails.description_url">Learn more</ExternalLink>
                </div>
            </div>
        </div>

        <!-- Slot list -->
        <div v-if="currentItem" class="composite-slots-container">
            <div v-if="slots.length === 0" class="text-muted text-center py-3">
                No component files defined for this type.
            </div>
            <CompositeSlotRow
                v-for="(slot, index) in slots"
                :key="slot.slotName"
                :slot-item="slot"
                @update:slotItem="(updated) => updateSlot(index, updated)" />

            <!-- Actions footer -->
            <div class="d-flex justify-content-end mt-2">
                <GButton
                    size="small"
                    outline
                    tooltip
                    title="Clear the type selection and all slot data"
                    @click="clearAll">
                    Reset
                </GButton>
            </div>
        </div>

        <!-- Empty state -->
        <div v-else class="composite-empty-state">
            <FontAwesomeIcon :icon="faLayerGroup" class="composite-empty-icon" />
            <p class="composite-empty-title">Select a Composite Type</p>
            <p class="composite-empty-subtitle">
                A composite dataset is made up of several component files that together form a single dataset in Galaxy
                (for example, a Plink dataset is three files:
                <code>.bed</code>, <code>.bim</code>, <code>.fam</code>).
            </p>
            <p class="composite-empty-subtitle">
                Choose a composite type from the dropdown above to see the required files.
            </p>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.composite-file-upload {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.composite-config-panel {
    flex-shrink: 0;
    padding: 0.75rem;
    background-color: $gray-100;
    border-radius: $border-radius-base;
    border: $border-default;
}

.composite-config-field {
    flex: 1 1 15rem;
    min-width: 0;
}

.composite-config-field :deep(.multiselect__single) {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.composite-slots-container {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    padding-right: 0.25rem;
}

.composite-empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    color: $text-muted;
}

.composite-empty-icon {
    font-size: 3.5rem;
    color: $border-color;
    margin-bottom: 1.25rem;
}

.composite-empty-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: $text-color;
    margin-bottom: 0.5rem;
}

.composite-empty-subtitle {
    font-size: 0.9rem;
    max-width: 480px;
    margin-bottom: 0.25rem;
}
</style>
