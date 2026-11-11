<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import Alert from "@/components/Alert.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import InvocationList from "@/components/Workflow/Invocation/InvocationList.vue";

interface HistoryInvocationProps {
    historyId: string;
}

const props = defineProps<HistoryInvocationProps>();

const historyStore = useHistoryStore();
const loadError = ref<string | null>(null);

const history = computed(() => historyStore.getHistoryById(props.historyId, false));
const historyName = computed(() => history.value?.name ?? "...");

watch(
    () => props.historyId,
    async (historyId) => {
        loadError.value = null;
        if (!historyStore.getHistoryById(historyId, false)) {
            try {
                await historyStore.loadHistoryById(historyId);
            } catch (error) {
                loadError.value = errorMessageAsString(error);
            }
        }
    },
    { immediate: true },
);

const breadcrumbItems = computed(() => [
    { title: "Histories", to: "/histories/list" },
    {
        title: historyName.value,
        to: `/histories/view?id=${props.historyId}`,
        superText: historyStore.currentHistoryId === props.historyId ? "current" : undefined,
    },
    { title: "Workflow Invocations" },
]);
</script>

<template>
    <div class="d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <Alert v-if="loadError" :message="loadError" variant="error" />
        <InvocationList
            v-else
            :history-id="props.historyId"
            :no-data-message="`No Workflow Invocations to display for ${historyName}`" />
    </div>
</template>
