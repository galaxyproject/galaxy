<template>
    <b-modal id="cleanup-result-modal" v-model="showModal" :title="title" title-tag="h2" hide-footer static>
        <div class="text-center">
            <b-spinner v-if="isLoading" class="mx-auto" data-test-id="loading-spinner" />
            <div v-else>
                <b-alert v-if="result.hasFailed" show variant="danger" data-test-id="error-alert">
                    {{ result.errorMessage }}
                </b-alert>
                <h3 v-else-if="result.success" data-test-id="success-info">
                    You've cleared <b>{{ result.niceTotalFreeBytes }}</b>
                </h3>
                <div v-else-if="result.isPartialSuccess" data-test-id="partial-success-info">
                    <h3>
                        You've successfully cleared <b>{{ result.totalCleaned }}</b> items for a total of
                        <b>{{ result.niceTotalFreeBytes }}</b> but...
                    </h3>
                    <b-alert v-if="result.hasSomeErrors" show variant="warning">
                        <h3 class="mb-0">
                            <b>{{ result.errors.length }}</b> items couldn't be cleared
                        </h3>
                    </b-alert>
                </div>
                <b-table-lite
                    v-if="result.hasSomeErrors"
                    :fields="errorFields"
                    :items="result.errors"
                    small
                    data-test-id="errors-table" />
            </div>
        </div>
    </b-modal>
</template>

<script>
import _l from "utils/localization";
import { CleanupResult } from "./model";

export default {
    props: {
        result: {
            type: CleanupResult,
            required: false,
            default: null,
        },
        show: {
            type: Boolean,
            required: false,
        },
    },
    data() {
        return {
            showModal: false,
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
    created() {
        this.showModal = this.show;
    },
};
</script>
