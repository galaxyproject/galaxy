<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
//@ts-ignore
import { errorMessageAsString } from "utils/simple-error";
import { computed, ref } from "vue";

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
        await axios.post(`${getAppRoot}/api/histories/${props.historyId}`);
        imported.value = true;
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
};

async function fetchName(historyId: string) {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/histories/${historyId}`);
        name.value = data?.name || "";
    } catch (error) {
        console.error("Error fetching history name:", error);
        name.value = "";
    }
}

fetchName(props.historyId);
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
            <span>Failed to Import History: {{ name }}!</span>
            <span>{{ error }}</span>
        </div>
    </div>
</template>
