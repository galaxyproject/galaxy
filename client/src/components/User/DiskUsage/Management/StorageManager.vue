<script setup lang="ts">
import { ref } from "vue";

import { useConfig } from "@/composables/config";
import localize from "@/utils/localization";
import { wait } from "@/utils/utils";

import { useCleanupCategories } from "./Cleanup/categories";
import type { CleanableItem, CleanupOperation, CleanupResult } from "./Cleanup/model";

import CleanupOperationSummary from "./Cleanup/CleanupOperationSummary.vue";
import CleanupResultDialog from "./Cleanup/CleanupResultDialog.vue";
import ReviewCleanupDialog from "./Cleanup/ReviewCleanupDialog.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

interface ModalDialog {
    openModal: () => void;
}

const breadcrumbItems = [
    { title: "存储仪表盘", to: "StorageDashboard" },
    { title: "管理您的账户存储", superText: "(测试版)" },
];

const { config } = useConfig();
const { cleanupCategories } = useCleanupCategories();

const currentOperation = ref<CleanupOperation>();
const currentTotalItems = ref(0);
const cleanupResult = ref<CleanupResult>();
const refreshOperationId = ref<string>();

const reviewModal = ref<ModalDialog | null>(null);
const resultModal = ref<ModalDialog | null>(null);

const issuesUrl = "https://github.com/galaxyproject/galaxy/issues";

function onReviewItems(operation: CleanupOperation, totalItems: number) {
    currentOperation.value = operation;
    currentTotalItems.value = totalItems;
    refreshOperationId.value = undefined;
    reviewModal.value?.openModal();
}

async function onConfirmCleanupSelected(selectedItems: CleanableItem[]) {
    cleanupResult.value = undefined;
    resultModal.value?.openModal();
    await wait(1000);
    if (currentOperation.value) {
        cleanupResult.value = await currentOperation.value.cleanupItems(selectedItems);
        if (cleanupResult.value.hasUpdatedResults) {
            refreshOperationId.value = currentOperation.value.id.toString();
        }
    }
}
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <b-row class="justify-content-md-center">
            <b-alert show dismissible variant="warning">
            {{ localize("此功能目前处于测试阶段，如果您发现任何问题，请在") }}
            <b-link :href="issuesUrl" target="_blank">此处</b-link>
            {{ localize("报告。") }}
            </b-alert>
        </b-row>
        <b-row class="justify-content-md-center mb-5">
            <b-alert v-if="config?.enable_quotas" show>
            {{ localize("存储管理器仅显示计入您的磁盘配额的元素。") }}
            <b-link :href="config.quota_url" target="_blank">{{ localize("了解更多") }}</b-link>
            </b-alert>
        </b-row>

        <div id="categories-panel">
            <b-container v-for="category in cleanupCategories" :key="category.id">
                <b-row class="justify-content-md-center mb-2">
                    <h3>
                        <b>{{ category.name }}</b>
                    </h3>
                </b-row>
                <b-row class="justify-content-md-center mb-5">
                    <b-card-group deck>
                        <CleanupOperationSummary
                            v-for="operation in category.operations"
                            :key="operation.id"
                            :operation="operation"
                            :refresh-operation-id="refreshOperationId"
                            @onReviewItems="onReviewItems" />
                    </b-card-group>
                </b-row>
            </b-container>
        </div>

        <ReviewCleanupDialog
            ref="reviewModal"
            :operation="currentOperation"
            :total-items="currentTotalItems"
            @onConfirmCleanupSelectedItems="onConfirmCleanupSelected" />

        <CleanupResultDialog ref="resultModal" :result="cleanupResult" />
    </div>
</template>
