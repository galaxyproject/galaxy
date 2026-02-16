<script setup lang="ts">
import { faExclamationTriangle, faInfoCircle, faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormInput, BFormSelect } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type {
    CollectionCreationState,
    CollectionTypeOption,
    SupportedCollectionType,
} from "@/composables/upload/collectionTypes";

interface FileItem {
    name: string;
}

interface CollectionCreationConfigProps {
    /** Array of file items for validation and pairing preview */
    files: FileItem[];
}

const props = defineProps<CollectionCreationConfigProps>();

const emit = defineEmits<{
    (e: "update:state", state: CollectionCreationState): void;
}>();

const isCreateCollectionActive = ref(false);
const collectionName = ref("");
const collectionType = ref<SupportedCollectionType>("list");

const collectionTypeOptions: CollectionTypeOption[] = [
    { value: "list", text: "List" },
    { value: "list:paired", text: "List of Pairs" },
];

const collectionValidation = computed(() => {
    if (!isCreateCollectionActive.value) {
        return { valid: true, message: "" };
    }

    if (!collectionName.value.trim()) {
        return { valid: false, message: "Collection name is required" };
    }

    const fileCount = props.files.length;

    if (collectionType.value === "list:paired") {
        if (fileCount < 2) {
            return { valid: false, message: "List of pairs requires at least 2 files" };
        }
        if (fileCount % 2 !== 0) {
            return { valid: false, message: "List of pairs requires an even number of files" };
        }
    } else if (collectionType.value === "list") {
        if (fileCount < 1) {
            return { valid: false, message: "List requires at least 1 file" };
        }
    }

    return { valid: true, message: "" };
});

// Pairing preview for list:paired
const filePairs = computed(() => {
    if (collectionType.value !== "list:paired" || !props.files) {
        return [];
    }

    const pairs = [];
    for (let i = 0; i < props.files.length; i += 2) {
        if (i + 1 < props.files.length) {
            pairs.push({
                index: i / 2,
                forward: props.files[i],
                reverse: props.files[i + 1],
            });
        }
    }
    return pairs;
});

// Emit state updates when collection configuration changes
watch(
    [isCreateCollectionActive, collectionName, collectionType, collectionValidation],
    () => {
        const config =
            isCreateCollectionActive.value && collectionValidation.value.valid
                ? {
                      name: collectionName.value.trim(),
                      type: collectionType.value,
                  }
                : null;

        emit("update:state", {
            config,
            validation: {
                isActive: isCreateCollectionActive.value,
                isValid: collectionValidation.value.valid,
                message: collectionValidation.value.message,
            },
        });
    },
    { immediate: true },
);

/** Reset the collection configuration to initial state */
function reset() {
    isCreateCollectionActive.value = false;
    collectionName.value = "";
    collectionType.value = "list";
}

defineExpose({ reset });
</script>

<template>
    <div class="collection-section mt-3">
        <div class="d-flex align-items-center justify-content-between">
            <BFormCheckbox v-model="isCreateCollectionActive" switch>
                <strong>Create a collection from these files</strong>
            </BFormCheckbox>
            <a
                href="https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/collections/tutorial.html"
                target="_blank"
                rel="noopener noreferrer"
                class="small text-muted">
                <FontAwesomeIcon :icon="faQuestionCircle" class="mr-1" />
                Learn more about dataset collections in Galaxy
            </a>
        </div>

        <div v-if="isCreateCollectionActive" class="collection-config mt-2">
            <div class="row g-2">
                <div class="col-md-8">
                    <label for="collection-name-input" class="form-label small mb-1">
                        Collection Name
                        <span class="text-danger">*</span>
                    </label>
                    <BFormInput
                        id="collection-name-input"
                        v-model="collectionName"
                        size="sm"
                        placeholder="Enter collection name"
                        :state="collectionValidation.valid ? null : false" />
                </div>
                <div class="col-md-4">
                    <label for="collection-type-select" class="form-label small mb-1"> Collection Type </label>
                    <BFormSelect
                        id="collection-type-select"
                        v-model="collectionType"
                        size="sm"
                        :options="collectionTypeOptions" />
                </div>
            </div>

            <!-- Validation Message -->
            <div v-if="!collectionValidation.valid" class="text-danger small mt-1">
                <FontAwesomeIcon :icon="faExclamationTriangle" class="mr-1" />
                {{ collectionValidation.message }}
            </div>

            <!-- Pairing Preview for list:paired -->
            <div v-if="collectionType === 'list:paired' && filePairs.length > 0" class="pairing-preview mt-2">
                <div class="small text-muted mb-1">
                    <strong>Pairing Preview:</strong>
                    Files will be paired consecutively
                </div>
                <div class="pairs-list">
                    <div v-for="pair in filePairs" :key="pair.index" class="pair-item small d-flex align-items-center">
                        <span class="pair-number">{{ pair.index + 1 }}.</span>
                        <span v-if="pair.forward && pair.reverse" class="pair-files">
                            <span class="badge badge-primary mr-1">Forward</span>
                            {{ pair.forward.name }}
                            <span class="mx-2">+</span>
                            <span class="badge badge-success mr-1">Reverse</span>
                            {{ pair.reverse.name }}
                        </span>
                    </div>
                    <div v-if="files.length % 2 !== 0" class="text-warning small mt-1">
                        <FontAwesomeIcon :icon="faExclamationTriangle" />
                        Last file will be skipped (odd number of files)
                    </div>
                </div>
            </div>

            <!-- Info about source items -->
            <div class="small text-muted mt-2">
                <FontAwesomeIcon :icon="faInfoCircle" class="mr-1" />
                Files will be uploaded directly into the collection
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.collection-section {
    padding: 0.75rem;
    background-color: lighten($gray-100, 2%);
    border-radius: $border-radius-base;
    border: 1px solid $border-color;

    .collection-config {
        padding-top: 0.5rem;
        border-top: 1px solid $border-color;
    }

    .pairing-preview {
        background-color: $white;
        border: 1px solid $border-color;
        border-radius: $border-radius-base;
        padding: 0.5rem;

        .pairs-list {
            max-height: 200px;
            overflow-y: auto;
        }

        .pair-item {
            padding: 0.25rem 0;
            border-bottom: 1px solid lighten($border-color, 5%);

            &:last-child {
                border-bottom: none;
            }

            .pair-number {
                font-weight: 600;
                min-width: 30px;
                color: $text-muted;
            }

            .pair-files {
                flex: 1;
                word-break: break-word;

                .badge {
                    font-size: 0.7rem;
                    padding: 0.15rem 0.4rem;
                }
            }
        }
    }
}
</style>
