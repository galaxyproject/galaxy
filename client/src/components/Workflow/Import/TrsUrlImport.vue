<script setup lang="ts">
import { BButton, BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, ref } from "vue";

interface Props {
    queryTrsUrl?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onImport", url: string): void;
}>();

const trsUrl = ref(props.queryTrsUrl);

const isImportDisabled = computed(() => {
    return !trsUrl.value;
});

const importTooltip = computed(() => {
    return isImportDisabled.value ? "You must provide a TRS URL." : "Import workflow from TRS URL";
});

function submit(ev: SubmitEvent) {
    ev.preventDefault();

    if (trsUrl.value) {
        emit("onImport", trsUrl.value);
    }
}

// Automatically trigger the import if the TRS URL was provided as a query param
if (trsUrl.value) {
    emit("onImport", trsUrl.value);
}
</script>

<template>
    <BForm class="mt-4" @submit="submit">
        <h2 class="h-sm">alternatively, provide a TRS URL directly</h2>

        <BFormGroup label="TRS URL:" label-class="font-weight-bold">
            <BFormInput id="trs-import-url-input" v-model="trsUrl" aria-label="TRS URL" type="url" />
            If the workflow is accessible via a TRS URL, enter the URL above and click Import.
        </BFormGroup>

        <BButton
            id="trs-url-import-button"
            type="submit"
            :disabled="isImportDisabled"
            :title="importTooltip"
            variant="primary">
            Import workflow
        </BButton>
    </BForm>
</template>
