<script setup lang="ts">
import localize from "@/utils/localization";
import { delay } from "@/utils/utils";
import { computed, ref, onMounted, watchEffect } from "vue";
import { BAlert, BCard, BCardText, BLink } from "bootstrap-vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import type { CleanableSummary, CleanupOperation } from "./model";

interface CleanupOperationSummaryProps {
    operation: CleanupOperation;
    refreshOperationId?: string;
    refreshDelay?: number;
}

const props = withDefaults(defineProps<CleanupOperationSummaryProps>(), {
    refreshOperationId: undefined,
    refreshDelay: 500,
});

const summary = ref<CleanableSummary>();
const loading = ref(true);
const errorMessage = ref<string>();

const canClearItems = computed(() => {
    return (summary.value?.totalItems ?? 0) > 0;
});

const emit = defineEmits<{
    (e: "onReviewItems", operation: CleanupOperation, totalItems: number): void;
}>();

onMounted(async () => {
    await refresh();
});

watchEffect(async () => {
    if (props.operation.id === props.refreshOperationId) {
        await refresh();
    }
});

async function refresh() {
    loading.value = true;
    try {
        const start = Date.now();
        summary.value = await props.operation.fetchSummary();
        const duration = Date.now() - start;
        await delay(props.refreshDelay - duration);
    } catch (error) {
        onError(String(error));
    } finally {
        loading.value = false;
    }
}

function onError(message: string) {
    errorMessage.value = message;
}

function onReviewItems() {
    emit("onReviewItems", props.operation, summary.value?.totalItems ?? 0);
}
</script>

<template>
    <b-card
        :title="props.operation.name"
        class="operation-card mx-2"
        footer-bg-variant="white"
        footer-border-variant="white">
        <loading-span v-if="loading" />
        <b-card-text v-if="!loading">
            {{ operation.description }}
        </b-card-text>
        <template v-slot:footer>
            <div v-if="!loading">
                <b-alert v-if="errorMessage" variant="danger" show data-test-id="error-alert">
                    <h2 class="alert-heading h-sm">Failed to retrieve details.</h2>
                    {{ errorMessage }}
                </b-alert>
                <b-link
                    v-else-if="summary && canClearItems"
                    href="#"
                    class="card-link"
                    data-test-id="review-link"
                    @click="onReviewItems">
                    <b>{{ localize("Review and clear") }} {{ summary.niceTotalSize }}</b>
                </b-link>
                <b v-else class="text-secondary" data-test-id="no-items-indicator">
                    {{ localize("No items to clear") }}
                </b>
            </div>
        </template>
    </b-card>
</template>

<style scoped>
.operation-card {
    text-align: center;
    width: 500px;
}
</style>
