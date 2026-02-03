<script setup lang="ts">
import { BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    queryTrsUrl?: string;
    hideSubmitButton?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    hideSubmitButton: false,
});

const emit = defineEmits<{
    (e: "onImport", url: string): void;
    (e: "input-valid", valid: boolean): void;
}>();

const trsUrl = ref(props.queryTrsUrl);

const isImportDisabled = computed(() => {
    return !trsUrl.value;
});

const importTooltip = computed(() => {
    return isImportDisabled.value ? "You must provide a TRS URL." : "Import workflow from TRS URL";
});

// Validation state for wizard mode
const isValid = computed(() => {
    return trsUrl.value !== null && trsUrl.value !== undefined && trsUrl.value.length > 0;
});

watch(
    isValid,
    (newValue) => {
        emit("input-valid", newValue);
    },
    { immediate: true }
);

// Hide submit button in wizard mode (or when hideSubmitButton is true)
const showSubmitButton = computed(() => {
    return !props.hideSubmitButton;
});

function submit(ev: SubmitEvent) {
    ev.preventDefault();

    if (trsUrl.value) {
        emit("onImport", trsUrl.value);
    }
}

// Expose method for wizard submit
function triggerImport() {
    if (trsUrl.value) {
        emit("onImport", trsUrl.value);
    }
}

defineExpose({ triggerImport });
</script>

<template>
    <BForm class="mt-4" @submit="submit">
        <h2 class="h-sm">Import from TRS URL</h2>

        <BFormGroup label="TRS URL:" label-class="font-weight-bold">
            <BFormInput id="trs-import-url-input" v-model="trsUrl" aria-label="TRS URL" type="url" />
            If the workflow is accessible via a TRS URL, enter the URL above and click Import.
        </BFormGroup>

        <GButton
            v-if="showSubmitButton"
            id="trs-url-import-button"
            type="submit"
            :disabled="isImportDisabled"
            :title="importTooltip"
            tooltip
            color="blue">
            Import workflow
        </GButton>
    </BForm>
</template>
