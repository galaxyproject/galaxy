<template>
    <b-modal id="cleanup-result-modal" :title="title" title-tag="h2" hide-footer>
        <div class="text-center">
            <b-spinner v-if="isLoading" class="mx-auto" />
            <b-alert v-else-if="hasFailed" show variant="danger">
                {{ localResult.errorMessage }}
            </b-alert>
            <h3 v-else-if="success">
                You've cleared <b>{{ niceTotalSpaceFreed }}</b>
            </h3>
            <b-alert v-if="hasSomeErrors" show variant="danger">
                {{ localResult.errors.length }} items couldn't be cleared
            </b-alert>
        </div>
    </b-modal>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import { CleanupResult } from "./model";

export default {
    props: {
        result: {
            type: CleanupResult,
            required: false,
            default: null,
        },
    },
    data() {
        return {
            localResult: null,
        };
    },
    computed: {
        /** @returns {Boolean} */
        isLoading() {
            return this.localResult === null;
        },
        /** @returns {Boolean} */
        hasFailed() {
            return this.localResult?.errorMessage !== null;
        },
        /** @returns {Boolean} */
        success() {
            return this.localResult?.success;
        },
        /** @returns {Boolean} */
        hasSomeErrors() {
            return this.localResult?.errors.length;
        },
        /** @returns {String} */
        niceTotalSpaceFreed() {
            return bytesToString(this.localResult?.totalFreeBytes, true);
        },
        /** @returns {String} */
        title() {
            let message = _l("Something went wrong...");
            if (this.isLoading) {
                message = _l("Freeing up some space...");
            }
            if (this.success) {
                message = _l("Congratulations!");
            }
            return message;
        },
    },
    watch: {
        result(newValue) {
            this.localResult = newValue;
        },
    },
};
</script>
