<template>
    <b-container fluid>
        <b-link to="StorageDashboard">Back to Dashboard</b-link>
        <h2 class="text-center my-3">
            <b>{{ title }}</b>
        </h2>

        <b-row class="justify-content-md-center mb-5">
            <b-alert v-if="quotaSettings.quotasEnabled" show>
                {{ whatCountsText }}
                <b-link :href="quotaSettings.quotasHelpUrl" target="_blank">{{ learnMoreText }}</b-link>
            </b-alert>
        </b-row>

        <div v-for="category in cleanupManager.categories" :key="category.id">
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
        </div>

        <ReviewCleanupDialog
            :operation="currentOperation"
            :total-items="currentTotalItems"
            @onConfirmCleanupSelectedItems="onConfirmCleanupSelected" />

        <CleanUpResultDialog :result="cleanupResult" />
    </b-container>
</template>

<script>
import _l from "utils/localization";
import { getGalaxyInstance } from "app";
import { QuotaSettings } from "../model";
import { ResourceCleanupManager } from "./Cleanup";
import CleanupOperationSummary from "./Cleanup/CleanupOperationSummary";
import CleanUpResultDialog from "./Cleanup/CleanUpResultDialog";
import ReviewCleanupDialog from "./Cleanup/ReviewCleanupDialog";

export default {
    components: {
        CleanupOperationSummary,
        ReviewCleanupDialog,
        CleanUpResultDialog,
    },
    data() {
        return {
            title: _l("Manage your account storage"),
            whatCountsText: _l("The storage manager only shows files that count towards your disk quota."),
            learnMoreText: _l("Learn more"),
            cleanupManager: null,
            quotaSettings: null,
            errorMessage: null,
            currentOperation: null,
            currentTotalItems: 0,
            cleanupResult: null,
            refreshOperationId: null,
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        this.quotaSettings = QuotaSettings.create(Galaxy.config);
        this.cleanupManager = ResourceCleanupManager.create();
    },
    methods: {
        onReviewItems(operationId, totalItems) {
            this.currentOperation = this.cleanupManager.getOperationById(operationId);
            this.currentTotalItems = totalItems;
            this.refreshOperationId = null;
            this.$bvModal.show("review-cleanup-dialog");
        },
        async onConfirmCleanupSelected(items) {
            this.$bvModal.show("cleanup-result-modal");
            this.cleanupResult = await this.currentOperation.cleanupItems(items);
            if (this.cleanupResult.success) {
                this.refreshOperationId = this.currentOperation.id.toString();
            }
        },
    },
};
</script>
