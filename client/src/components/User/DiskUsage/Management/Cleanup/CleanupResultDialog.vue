<template>
    <b-modal id="cleanup-result-modal" :title="title" title-tag="h2" hide-footer @hidden="onHide">
        <div class="text-center">
            <b-spinner v-if="isLoading" class="mx-auto" />
            <b-alert v-else-if="hasErrored" show variant="danger">
                {{ result.errorMessage }}
            </b-alert>
            <h3 v-else>
                You've cleared <b>{{ niceTotalSpaceFreed }}</b>
            </h3>
        </div>
    </b-modal>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import { CleanupResult } from "../../model";

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
        hasErrored() {
            return this.localResult?.errorMessage !== null;
        },
        /** @returns {String} */
        niceTotalSpaceFreed() {
            return bytesToString(this.localResult?.totalFreeBytes, true);
        },
        /** @returns {String} */
        title() {
            if (this.isLoading) {
                return _l("Freeing up some space...");
            }
            return this.hasErrored ? _l("Something went wrong...") : _l("Congratulations!");
        },
    },
    methods: {
        onHide() {
            this.$emit("onHide");
        },
    },
    watch: {
        result(newValue) {
            this.localResult = newValue;
        },
    },
};
</script>
