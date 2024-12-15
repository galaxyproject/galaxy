<script setup lang="ts">
import { BAlert, BCard, BCardTitle } from "bootstrap-vue";
import { ref, watch } from "vue";

import { getGalaxyInstance } from "@/app";
import { useTableSummary } from "@/components/Collections/tables";
import { errorMessageAsString } from "@/utils/simple-error";
import { urlData } from "@/utils/url";

import JaggedDataAlert from "./JaggedDataAlert.vue";

const emit = defineEmits(["onChange", "onError"]);
const errorMessage = ref<string | undefined>(undefined);
const { rawValue, jaggedDataWarning, table } = useTableSummary();

async function fetchAndHandleData(response: Record) {
    const selectedDatasetId = response.id;
    const historyId = response.history_id;
    try {
        const newSourceContent = await urlData({
            url: `/api/histories/${historyId}/contents/${selectedDatasetId}/display`,
        });
        rawValue.value = newSourceContent as string;
    } catch (error) {
        rawValue.value = "";
        errorMessage.value = errorMessageAsString(error);
    }
}

interface Record {
    id: string;
    history_id: string;
}

function inputDialog() {
    const Galaxy = getGalaxyInstance();
    Galaxy.data.dialog(fetchAndHandleData, {
        multiple: false,
        library: false,
        format: null,
        allowUpload: false,
    });
}

watch(table, (newValue: string[][]) => {
    emit("onChange", table.value);
});
</script>

<template>
    <BCard class="wizard-selection-card" border-variant="primary" @click="inputDialog">
        <BCardTitle>
            <b>Select dataset</b>
        </BCardTitle>
        <div>
            <BAlert v-if="errorMessage" show variant="danger">{{ errorMessage }}</BAlert>
            <JaggedDataAlert :jaggedDataWarning="jaggedDataWarning" />
            Select a history datasets, the contents will be loaded as tabular data and made available to the rule based
            import utility.
        </div>
    </BCard>
</template>
