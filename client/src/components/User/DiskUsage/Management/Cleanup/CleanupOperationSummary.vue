<template>
    <b-card :title="operation.name" class="item-counter-card mx-2">
        <b-alert v-if="errorMessage" variant="danger" show>
            <h4 class="alert-heading">Failed to retrieve details.</h4>
            {{ errorMessage }}
        </b-alert>
        <LoadingSpan v-if="loading" />
        <div v-else>
            <b-card-text>
                {{ operation.description }}
            </b-card-text>

            <b-link v-if="canClearItems" href="#" class="card-link" @click="onReviewItems">
                <b>{{ reviewAndClearText }} {{ summary.niceTotalSize }}</b>
            </b-link>
            <b v-else class="text-secondary">
                {{ noItemsToClearText }}
            </b>
        </div>
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
    async created() {
        await this.refresh();
    },
    computed: {
        /** @returns {Boolean} */
        canClearItems() {
            return this.summary.totalItems > 0;
        },
    },
    methods: {
        async refresh() {
            this.loading = true;
            try {
                const start = Date.now();
                this.summary = await this.operation.fetchSummary();
                const duration = Date.now() - start;
                await delay(this.refreshDelay - duration);
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
    watch: {
        /** The parent signaled that `operationId` must be updated */
        async refreshOperationId(operationId) {
            if (this.operation.id === operationId) {
                await this.refresh();
            }
        },
    },
};
</script>

<style scoped>
.item-counter-card {
    text-align: center;
    width: 500px;
}
</style>
