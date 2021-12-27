<template>
    <b-card :title="title" class="item-counter-card mx-2">
        <b-alert v-if="errorMessage" variant="danger" show>
            <h4 class="alert-heading">Failed to retrieve details.</h4>
            {{ errorMessage }}
        </b-alert>
        <LoadingSpan v-if="loading" />
        <div v-else>
            <b-card-text>
                {{ description }}
            </b-card-text>

            <b-link v-if="canClearItems" href="#" class="card-link" @click="onReviewItems">
                <b>{{ reviewAndClearText }} {{ totalRecoverableAmount }}</b>
            </b-link>
            <b-card-footer v-else>
                {{ noItemsToClearText }}
            </b-card-footer>
        </div>
    </b-card>
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
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            required: true,
        },
        providerCallback: {
            type: Promise,
            required: true,
        },
    },
    data() {
        return {
            noItemsToClearText: _l("No items to clear"),
            reviewAndClearText: _l("Review and clear"),
            items: null,
            loading: true,
            errorMessage: null,
        };
    },
    async created() {
        this.loading = true;
        try {
            this.items = await this.providerCallback();
        } finally {
            this.loading = false;
        }
    },
    computed: {
        /** @returns {float} */
        totalRecoverableBytes() {
            return this.items
                ? this.items.reduce(function (acc, obj) {
                      return acc + obj.size;
                  }, 0)
                : 0;
        },
        /** @returns {String} */
        totalRecoverableAmount() {
            return bytesToString(this.totalRecoverableBytes, true);
        },
        /** @returns {Boolean} */
        canClearItems() {
            return this.items?.length > 0;
        },
    },
    methods: {
        onError(err) {
            this.errorMessage = err;
        },
        onReviewItems() {
            this.$emit("onReviewItems", this.items);
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
