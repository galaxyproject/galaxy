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
import Heading from "@/components/Common/Heading.vue";

interface ModalDialog {
    openModal: () => void;
}

const breadcrumbItems = [
    { title: "Storage Dashboard", to: { name: "StorageDashboard" } },
    { title: "Manage your account storage" },
];

const { config } = useConfig();
const { cleanupCategories } = useCleanupCategories();

const currentOperation = ref<CleanupOperation>();
const currentTotalItems = ref(0);
const cleanupResult = ref<CleanupResult>();
const refreshOperationId = ref<string>();

const reviewModal = ref<ModalDialog | null>(null);
const resultModal = ref<ModalDialog | null>(null);

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

        <Heading v-if="config?.enable_quotas" h2 size="sm">
            {{ localize("The storage manager only shows elements that count towards your disk quota.") }}
            <a :href="config.quota_url" target="_blank">{{ localize("Click here to learn more.") }}</a>
        </Heading>

        <div v-for="category in cleanupCategories" :key="category.id" class="mx-3 mb-4">
            <h4 class="mb-3">
                <b>{{ category.name }}</b>
            </h4>
            <b-card-group deck>
                <CleanupOperationSummary
                    v-for="operation in category.operations"
                    :key="operation.id"
                    :operation="operation"
                    :refresh-operation-id="refreshOperationId"
                    @onReviewItems="onReviewItems" />
            </b-card-group>
        </div>

        <ReviewCleanupDialog
            ref="reviewModal"
            :operation="currentOperation"
            :total-items="currentTotalItems"
            @onConfirmCleanupSelectedItems="onConfirmCleanupSelected" />

        <CleanupResultDialog ref="resultModal" :result="cleanupResult" />
    </div>
</template>
