<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormGroup } from "bootstrap-vue";
import { computed, ref } from "vue";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GTooltip from "@/components/BaseComponents/GTooltip.vue";

interface Props {
    includeFiles: boolean;
    includeDeleted: boolean;
    includeHidden: boolean;
    disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    disabled: false,
});

const emit = defineEmits<{
    (e: "update:include-files", value: boolean): void;
    (e: "update:include-deleted", value: boolean): void;
    (e: "update:include-hidden", value: boolean): void;
}>();

const datasetsMappingInfoRef = ref<HTMLElement | null>(null);

const DATASETS_MAPPING_DISCLAIMER =
    "It is a convenience summary: the complete metadata is in datasets_attrs.txt, also included in the archive.";

const datasetsMappingDetails = computed(() =>
    props.includeFiles
        ? "Files in the archive are renamed to keep them unique, so they don't match the dataset names in your " +
          "history. datasets_mapping.tsv links each file back to its dataset (HID, name, format, collection " +
          "element, tags), so you can tell which file is which and track your samples with any spreadsheet tool. " +
          DATASETS_MAPPING_DISCLAIMER
        : "datasets_mapping.tsv lists every exported dataset (HID, name, format, collection element, tags) in a " +
          "table you can open with any spreadsheet tool. " +
          DATASETS_MAPPING_DISCLAIMER,
);
</script>

<template>
    <BFormGroup label="Dataset files included in the export:">
        <!-- GCheckbox renders inline, so stack the switches here -->
        <div class="d-flex flex-column align-items-start">
            <GCheckbox
                :model-value="props.includeFiles"
                :disabled="props.disabled"
                switch
                data-test-id="include-files-checkbox"
                @update:model-value="emit('update:include-files', $event)">
                Include Active Files
            </GCheckbox>

            <GCheckbox
                :model-value="props.includeDeleted"
                :disabled="props.disabled"
                switch
                data-test-id="include-deleted-checkbox"
                @update:model-value="emit('update:include-deleted', $event)">
                Include Deleted (not purged)
            </GCheckbox>

            <GCheckbox
                :model-value="props.includeHidden"
                :disabled="props.disabled"
                switch
                data-test-id="include-hidden-checkbox"
                @update:model-value="emit('update:include-hidden', $event)">
                Include Hidden
            </GCheckbox>
        </div>

        <template v-slot:description>
            <span
                ref="datasetsMappingInfoRef"
                class="datasets-mapping-info"
                tabindex="0"
                data-test-id="datasets-mapping-info">
                <FontAwesomeIcon :icon="faInfoCircle" class="mr-1" aria-hidden="true" />
                Includes <code>datasets_mapping.tsv</code> to help you find your data in the archive.
            </span>
            <GTooltip :reference="datasetsMappingInfoRef">
                <div class="datasets-mapping-details">{{ datasetsMappingDetails }}</div>
            </GTooltip>
        </template>
    </BFormGroup>
</template>

<style scoped>
/* GTooltip sizes to max-content, so cap the width to wrap the long explanation. */
.datasets-mapping-details {
    max-width: 22rem;
}
</style>
