<template>
    <b-modal id="cleanup-result-modal" :title="title" title-tag="h2" hide-footer>
        <div class="text-center">
            <b-spinner v-if="isLoading" class="mx-auto" />
            <div v-else>
                <b-alert v-if="result.hasFailed" show variant="danger">
                    {{ result.errorMessage }}
                </b-alert>
                <div v-else-if="result.isPartialSuccess">
                    <h3>
                        You've successfully cleared <b>{{ result.totalCleaned }}</b> items for a total of
                        <b>{{ niceTotalSpaceFreed }}</b> but...
                    </h3>
                    <b-alert v-if="result.hasSomeErrors" show variant="warning">
                        <h3 class="mb-0">
                            <b>{{ result.errors.length }}</b> items couldn't be cleared
                        </h3>
                    </b-alert>
                    <b-table-lite :fields="errorFields" :items="result.errors" small />
                </div>
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
    data() {
        return {
            errorFields: [
                { key: "name", label: _l("Name") },
                { key: "reason", label: _l("Reason") },
            ],
        };
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
                message = _l("Sorry, some items couldn't be cleared");
            } else if (this.result.success) {
                message = _l("Congratulations!");
            }
            return message;
        },
    },
};
</script>
