<template>
    <b-modal id="cleanup-result-modal" :title="title" title-tag="h2" hide-footer>
        <div class="text-center">
            <b-spinner v-if="isLoading" class="mx-auto" />
            <div v-else>
                <b-alert v-if="result.hasFailed" show variant="danger">
                    {{ result.errorMessage }}
                </b-alert>
                <b-alert v-else-if="result.hasSomeErrors" show variant="danger">
                    {{ result.errors.length }} items couldn't be cleared
                </b-alert>
                <h3 v-else-if="result.success">
                    You've cleared <b>{{ niceTotalSpaceFreed }}</b>
                </h3>
            </div>
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
    computed: {
        /** @returns {Boolean} */
        isLoading() {
            return this.result === null;
        },
        /** @returns {String} */
        niceTotalSpaceFreed() {
            return bytesToString(this.result?.totalFreeBytes, true);
        },
        /** @returns {String} */
        title() {
            let message = _l("Something went wrong...");
            if (this.isLoading) {
                message = _l("Freeing up some space...");
            } else if (this.result.isPartialSuccess) {
                message = _l("Some items couldn't be cleared");
            } else if (this.result.success) {
                message = _l("Congratulations!");
            }
            return message;
        },
    },
};
</script>
