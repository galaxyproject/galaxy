<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
//@ts-ignore
import { errorMessageAsString } from "utils/simple-error";
import { computed, ref, watch } from "vue";

import { fromCache } from "@/components/Markdown/cache";
import { getAppRoot } from "@/onload/loadConfig";

interface Props {
    historyId: string;
}

const props = defineProps<Props>();

const imported = ref(false);
const error = ref<string | null>(null);

const name = ref("");
const showLink = computed(() => !imported.value && !error.value);

const onClick = async () => {
    try {
        await axios.post(`${getAppRoot()}api/histories`, { history_id: props.historyId });
        imported.value = true;
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
};

async function fetchName(historyId: string) {
    try {
        const data = await fromCache(`histories/${historyId}`);
        name.value = data?.name || "";
    } catch (e) {
        error.value = errorMessageAsString(e);
        name.value = "";
    }
}

watch(
    () => props.historyId,
    () => fetchName(props.historyId),
    { immediate: true }
);
</script>

<template>
    <div>
        <b-link v-if="showLink" data-description="history import link" :data-history-id="historyId" @click="onClick">
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
