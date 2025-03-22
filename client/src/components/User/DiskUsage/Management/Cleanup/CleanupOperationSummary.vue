<script setup lang="ts">
import { BAlert, BCard, BCardText, BLink } from "bootstrap-vue";
import { computed, onMounted, ref, watchEffect } from "vue";

import localize from "@/utils/localization";
import { wait } from "@/utils/utils";

import type { CleanableSummary, CleanupOperation } from "./model";

import LoadingSpan from "@/components/LoadingSpan.vue";

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
        await wait(props.refreshDelay - duration);
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
    <BCard
        :title="props.operation.name"
        class="operation-card mx-2"
        footer-bg-variant="white"
        footer-border-variant="white">
        <LoadingSpan v-if="loading" />
        <BCardText v-if="!loading">
            {{ operation.description }}
        </BCardText>
        <template v-slot:footer>
            <div v-if="!loading">
                <BAlert v-if="errorMessage" variant="danger" show data-test-id="error-alert">
                    <h2 class="alert-heading h-sm">获取详细信息失败。</h2>
                    {{ errorMessage }}
                </BAlert>
                <BLink
                    v-else-if="summary && canClearItems"
                    href="#"
                    class="card-link"
                    data-test-id="review-link"
                    @click="onReviewItems">
                    <b>{{ localize("审核并清理") }} {{ summary.niceTotalSize }}</b>
                </BLink>
                <b v-else class="text-secondary" data-test-id="no-items-indicator">
                    {{ localize("没有可清理的项目") }}
                </b>
            </div>
        </template>
    </BCard>
</template>

<style scoped>
.operation-card {
    text-align: center;
    width: 500px;
}
</style>
