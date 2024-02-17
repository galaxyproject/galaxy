<script setup lang="ts">
import { computed, ref } from "vue";

const props = defineProps({
    queryTrsUrl: {
        type: String,
        default: null,
    },
});

const trsUrl = ref(props.queryTrsUrl);

const isImportDisabled = computed(() => {
    return !trsUrl.value;
});

const importTooltip = computed(() => {
    return isImportDisabled.value ? "You must provide a TRS URL." : "Import workflow from TRS URL";
});

const emit = defineEmits<{
    (e: "onImport", url: string): void;
}>();

function submit(ev: SubmitEvent) {
    ev.preventDefault();
    emit("onImport", trsUrl.value);
}

// Automatically trigger the import if the TRS URL was provided as a query param
if (trsUrl.value) {
    emit("onImport", trsUrl.value);
}
</script>

<template>
    <b-form class="mt-4" @submit="submit">
        <h2 class="h-sm">alternatively, provide a TRS URL directly</h2>
        <b-form-group label="TRS URL:" label-class="font-weight-bold">
            <b-form-input id="trs-import-url-input" v-model="trsUrl" aria-label="TRS URL" type="url" />
            If the workflow is accessible via a TRS URL, enter the URL above and click Import.
        </b-form-group>
        <b-button
            id="trs-url-import-button"
            type="submit"
            :disabled="isImportDisabled"
            :title="importTooltip"
            variant="primary">
            Import workflow
        </b-button>
    </b-form>
</template>
