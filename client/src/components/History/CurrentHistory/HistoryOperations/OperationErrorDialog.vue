<template>
    <b-modal
        v-model="show"
        title="Something went wrong..."
        header-text-variant="danger"
        title-tag="h2"
        scrollable
        ok-only
        @hide="onHide">
        <p v-if="isPartialSuccess" v-localize>
            -<strong>{{ success_count }}</strong
            >- items were processed successfully, unfortunately, -<strong>{{ error_count }}</strong
            >- items failed because of the following reasons:
        </p>
        <p v-else v-localize>The operation failed for the following reasons:</p>
        <div>
            <ul>
                <li v-for="(reason, index) in reasons" :key="`error-${index}`">
                    {{ reason }}
                </li>
            </ul>
        </div>
    </b-modal>
</template>

<script>
import { BModal } from "bootstrap-vue";
export default {
    components: {
        BModal,
    },
    props: {
        operationError: { type: Object, default: null },
    },
    data: function () {
        return {
            show: this.operationError != null,
        };
    },
    computed: {
        isPartialSuccess() {
            return this.operationError?.result?.success_count > 0;
        },
        success_count() {
            return this.operationError?.result?.success_count || 0;
        },
        error_count() {
            return this.operationError?.result?.errors.length || 0;
        },
        reasons() {
            if (this.operationError && this.operationError.result) {
                return [...new Set(this.operationError.result.errors.map((e) => e.error))];
            }
            return [];
        },
    },
    methods: {
        onHide() {
            this.$emit("hide");
        },
    },
};
</script>
