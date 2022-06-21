<template>
    <b-modal
        v-model="show"
        :title="title"
        :header-text-variant="titleVariant"
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
            <ul v-if="errorMessage">
                <li>{{ errorMessage }}</li>
            </ul>
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
            const response_error = this.operationError?.errorMessage?.response?.data?.err_msg;
            if (response_error) {
                return [response_error];
            }
            return [];
        },
        title() {
            return this.isPartialSuccess ? "Some items could not be processed" : "Something went wrong...";
        },
        titleVariant() {
            return this.isPartialSuccess ? "warning" : "danger";
        },
        errorMessage() {
            return this.operationError?.errorMessage?.message;
        },
    },
    methods: {
        onHide() {
            this.$emit("hide");
        },
    },
};
</script>
