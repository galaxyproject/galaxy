<template>
    <b-card :title="operation.name" class="operation-card mx-2" footer-bg-variant="white" footer-border-variant="white">
        <LoadingSpan v-if="loading" />
        <b-card-text v-if="!loading">
            {{ operation.description }}
        </b-card-text>
        <template v-slot:footer>
            <div v-if="!loading">
                <b-alert v-if="errorMessage" variant="danger" show data-test-id="error-alert">
                    <h4 class="alert-heading">Failed to retrieve details.</h4>
                    {{ errorMessage }}
                </b-alert>
                <b-link
                    v-else-if="canClearItems"
                    href="#"
                    class="card-link"
                    data-test-id="review-link"
                    @click="onReviewItems">
                    <b>{{ reviewAndClearText }} {{ summary.niceTotalSize }}</b>
                </b-link>
                <b v-else class="text-secondary" data-test-id="no-items-indicator">
                    {{ noItemsToClearText }}
                </b>
            </div>
        </template>
    </b-card>
</template>

<script>
import _l from "utils/localization";
import { delay } from "utils/utils";
import LoadingSpan from "components/LoadingSpan";
import { CleanupOperation } from "./model";

export default {
    components: {
        LoadingSpan,
    },
    props: {
        operation: {
            type: CleanupOperation,
            required: true,
        },
        refreshOperationId: {
            type: String,
            required: false,
            default: null,
        },
        refreshDelay: {
            type: Number,
            required: false,
            default: 500,
        },
    },
    data() {
        return {
            noItemsToClearText: _l("No items to clear"),
            reviewAndClearText: _l("Review and clear"),
            summary: null,
            loading: true,
            errorMessage: null,
        };
    },
    computed: {
        /** @returns {Boolean} */
        canClearItems() {
            return this.summary.totalItems > 0;
        },
    },
    watch: {
        /** The parent signaled that `operationId` must be updated */
        async refreshOperationId(operationId) {
            if (this.operation.id === operationId) {
                await this.refresh();
            }
        },
    },
    async created() {
        await this.refresh();
    },
    methods: {
        async refresh() {
            this.loading = true;
            try {
                const start = Date.now();
                this.summary = await this.operation.fetchSummary();
                const duration = Date.now() - start;
                await delay(this.refreshDelay - duration);
            } catch (error) {
                this.onError(error);
            } finally {
                this.loading = false;
            }
        },
        onError(err) {
            this.errorMessage = err;
        },
        onReviewItems() {
            this.$emit("onReviewItems", this.operation, this.summary.totalItems);
        },
    },
};
</script>

<style scoped>
.operation-card {
    text-align: center;
    width: 500px;
}
</style>
