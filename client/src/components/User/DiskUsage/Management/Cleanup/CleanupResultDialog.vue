<template>
    <b-modal id="cleanup-result-modal" :title="title" title-tag="h2" hide-footer @hide="onHide">
        <div class="text-center">
            <b-spinner v-if="isLoading" class="mx-auto" />
            <h3 v-else>
                You've cleared <b>{{ niceTotalSpaceFreed }}</b>
            </h3>
        </div>
    </b-modal>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";

export default {
    props: {
        result: {
            type: Object,
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
            return bytesToString(this.result.totalFreeBytes, true);
        },
        /** @returns {String} */
        title() {
            return this.isLoading ? _l("Freeing up some space...") : _l("Congratulations!");
        },
    },
    methods: {
        onHide() {
            this.$emit("onHide");
        },
    },
};
</script>
