<template>
    <ConfigProvider v-slot="{ config }">
        <b-container fluid>
            <b-link to="StorageDashboard">{{ goBackText }}</b-link>
            <h2 class="text-center my-3">
                <b>{{ title }}</b> <sup class="text-beta">(Beta)</sup>
            </h2>

            <b-row class="justify-content-md-center">
                <b-alert show dismissible variant="warning">
                    {{ betaText }}
                    <b-link :href="issuesUrl" target="_blank">here</b-link>.
                </b-alert>
            </b-row>
            <b-row class="justify-content-md-center mb-5">
                <b-alert v-if="config.enable_quotas" show>
                    {{ whatCountsText }}
                    <b-link :href="config.quota_url" target="_blank">{{ learnMoreText }}</b-link>
                </b-alert>
            </b-row>

            <CleanupCategoriesProvider v-slot="{ categories }">
                <div id="categories-panel">
                    <b-container v-for="category in categories" :key="category.id">
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
            </CleanupCategoriesProvider>

            <ReviewCleanupDialog
                :operation="currentOperation"
                :total-items="currentTotalItems"
                @onConfirmCleanupSelectedItems="onConfirmCleanupSelected" />

            <CleanupResultDialog :result="cleanupResult" />
        </b-container>
    </ConfigProvider>
</template>

<script>
import _l from "utils/localization";
import { delay } from "utils/utils";
import ConfigProvider from "components/providers/ConfigProvider";
import CleanupCategoriesProvider from "./Cleanup/cleanupCategoriesProvider";
import CleanupOperationSummary from "./Cleanup/CleanupOperationSummary";
import CleanupResultDialog from "./Cleanup/CleanupResultDialog";
import ReviewCleanupDialog from "./Cleanup/ReviewCleanupDialog";

export default {
    components: {
        ConfigProvider,
        CleanupOperationSummary,
        ReviewCleanupDialog,
        CleanupResultDialog,
        CleanupCategoriesProvider,
    },
    data() {
        return {
            goBackText: _l("Back to Dashboard"),
            title: _l("Manage your account storage"),
            whatCountsText: _l("The storage manager only shows elements that count towards your disk quota."),
            learnMoreText: _l("Learn more"),
            betaText: _l("This feature is currently in Beta, if you find any issues please report them"),
            issuesUrl: "https://github.com/galaxyproject/galaxy/issues",
            errorMessage: null,
            currentOperation: null,
            currentTotalItems: 0,
            cleanupResult: null,
            refreshOperationId: null,
        };
    },
    methods: {
        onReviewItems(operation, totalItems) {
            this.currentOperation = operation;
            this.currentTotalItems = totalItems;
            this.refreshOperationId = null;
            this.$bvModal.show("review-cleanup-dialog");
        },
        async onConfirmCleanupSelected(items) {
            this.cleanupResult = null;
            this.$bvModal.show("cleanup-result-modal");
            await delay(1000);
            this.cleanupResult = await this.currentOperation.cleanupItems(items);
            if (this.cleanupResult.success) {
                this.refreshOperationId = this.currentOperation.id.toString();
            }
        },
    },
};
</script>
<style lang="css" scoped>
.text-beta {
    color: #717273;
}
</style>
