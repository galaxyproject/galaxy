<script setup lang="ts">
import { faCheck, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BLink } from "bootstrap-vue";
import { computed, inject, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useHistoryStore } from "@/stores/historyStore";
//@ts-ignore
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    historyId: string;
}

const { getHistoryNameById } = useHistoryStore();

const props = defineProps<Props>();

const embed = inject("embed", false);
const historyUrl = computed(() => withPrefix(`/histories/view?id=${props.historyId}`));

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
        <a
            v-if="embed"
            data-description="history import link"
            :data-history-id="historyId"
            :href="historyUrl"
            target="_blank">
            Click to Import History: {{ name }}
        </a>
        <BLink
            v-else-if="showLink"
            data-description="history import link"
            :data-history-id="historyId"
            @click="onImport">
            Click to Import History: {{ name }}
        </BLink>
        <div v-if="imported" class="text-success">
            <FontAwesomeIcon :icon="faCheck" class="mr-1" />
            <span>Successfully Imported History: {{ name }}!</span>
        </div>
        <div v-if="!!error" class="text-danger">
            <FontAwesomeIcon :icon="faExclamationTriangle" class="mr-1" />
            <span>Failed to handle History: {{ name || "n/a" }}!</span>
            <span>{{ error }}</span>
        </div>
    </div>
</template>
