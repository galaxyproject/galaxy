<script setup lang="ts">
import { type AxiosError } from "axios";
import { BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type components } from "@/api/schema";

type HistoryContentBulkOperationResult = components["schemas"]["HistoryContentBulkOperationResult"];

interface OperationError {
    errorMessage: AxiosError & {
        response: {
            data: {
                err_msg: string;
            };
        };
    };
    result: HistoryContentBulkOperationResult;
}

interface Props {
    operationError: OperationError;
}

const props = defineProps<Props>();

const emit = defineEmits(["hide"]);

const show = ref(() => props.operationError != null);

const isPartialSuccess = computed(() => {
    return props.operationError?.result?.success_count > 0;
});
const success_count = computed(() => {
    return props.operationError?.result?.success_count || 0;
});
const error_count = computed(() => {
    return props.operationError?.result?.errors.length || 0;
});
const reasons = computed(() => {
    if (props.operationError && props.operationError.result) {
        return [...new Set(props.operationError.result.errors.map((e: any) => e.error))];
    }

    const response_error = props.operationError?.errorMessage?.response?.data?.err_msg;

    if (response_error) {
        return [response_error];
    }
    return [];
});
const title = computed(() => {
    return isPartialSuccess.value ? "Some items could not be processed" : "Something went wrong...";
});
const titleVariant = computed(() => {
    return isPartialSuccess.value ? "warning" : "danger";
});
const errorMessage = computed(() => {
    return props.operationError?.errorMessage?.message;
});

function onHide() {
    emit("hide");
}
</script>

<template>
    <BModal
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
    </BModal>
</template>
