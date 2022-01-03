<template>
    <b-modal id="cleanup-result-modal" title="Congratulations!" title-tag="h2" hide-footer>
        <LoadingSpan v-if="isLoading" :message="loadingMessage" />
        <div v-else class="d-block text-center">
            <h3>
                You successfully freed <b>{{ niceTotalSpaceFreed }}</b>
            </h3>
        </div>
    </b-modal>
</template>

<script>
import _l from "utils/localization";
import { bytesToString } from "utils/utils";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
    },
    props: {
        result: {
            type: Object,
            required: false,
            default: null,
        },
    },
    data() {
        return {
            loadingMessage: _l("Freeing up some space..."),
        };
    },
    computed: {
        /** @returns {Boolean} */
        isLoading() {
            return this.result == null;
        },
        /** @returns {String} */
        niceTotalSpaceFreed() {
            return bytesToString(this.result.totalFreeBytes, true);
        },
    },
};
</script>
