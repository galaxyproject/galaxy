<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
//@ts-ignore
import { errorMessageAsString } from "utils/simple-error";
import { computed, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useHistoryStore } from "@/stores/historyStore";

interface Props {
    historyId: string;
}

const { getHistoryNameById } = useHistoryStore();

const props = defineProps<Props>();

const imported = ref(false);
const error = ref<string | null>(null);

const name = computed(() => getHistoryNameById(props.historyId));
const showLink = computed(() => !imported.value && !error.value);

const onImport = async () => {
    try {
        await axios.post(`${getAppRoot()}api/histories`, { history_id: props.historyId });
        imported.value = true;
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
};
</script>

<template>
    <div>
        <b-link v-if="showLink" data-description="history import link" :data-history-id="historyId" @click="onImport">
            Click to Import History: {{ name }}.
        </b-link>
        <div v-if="imported" class="text-success">
            <FontAwesomeIcon icon="check" class="mr-1" />
            <span>Successfully Imported History: {{ name }}!</span>
        </div>
        <div v-if="!!error" class="text-danger">
            <FontAwesomeIcon icon="exclamation-triangle" class="mr-1" />
            <span>Failed to handle History: {{ name || "n/a" }}!</span>
            <span>{{ error }}</span>
        </div>
    </div>
</template>
