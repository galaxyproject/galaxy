<script setup lang="ts">
import { BAlert, BModal, BSpinner } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import localize from "@/utils/localization";

import type { CleanupResult } from "./model";

import Alert from "@/components/Alert.vue";
import GTable from "@/components/Common/GTable.vue";

interface CleanupResultDialogProps {
    result?: CleanupResult;
}

const props = withDefaults(defineProps<CleanupResultDialogProps>(), {
    result: undefined,
});

const showModal = ref(false);

const isLoading = computed<boolean>(() => {
    return props.result === undefined;
});

const title = computed<string>(() => {
    let message = localize("Something went wrong...");
    if (isLoading.value) {
        message = localize("Freeing up some space...");
    } else if (props.result?.isPartialSuccess) {
        message = localize("Sorry, some items couldn't be cleared");
    } else if (props.result?.success) {
        message = localize("Congratulations!");
    }
    return message;
});

const errorFields: TableField[] = [
    { key: "name", label: localize("Name") },
    { key: "reason", label: localize("Reason") },
];

function openModal() {
    showModal.value = true;
}

defineExpose({
    openModal,
});
</script>

<template>
    <BModal id="cleanup-result-modal" v-model="showModal" :title="title" title-tag="h2" hide-footer static>
        <div class="text-center">
            <Alert
                variant="info"
                message="After the operation, the storage space that will be freed up will only be for the unique items. This means that some items may not free up any storage space because they are duplicates of other items." />

            <BSpinner v-if="isLoading" class="mx-auto" data-test-id="loading-spinner" />
            <div v-else-if="result">
                <BAlert v-if="result.hasFailed" show variant="danger" data-test-id="error-alert">
                    {{ result.errorMessage }}
                </BAlert>
                <h3 v-else-if="result.success" data-test-id="success-info">
                    You've cleared <b>{{ result.niceTotalFreeBytes }}</b>
                </h3>
                <div v-else-if="result.isPartialSuccess" data-test-id="partial-success-info">
                    <h3>
                        You've successfully cleared <b>{{ result.totalCleaned }}</b> items for a total of
                        <b>{{ result.niceTotalFreeBytes }}</b> but...
                    </h3>
                    <BAlert v-if="result.hasSomeErrors" show variant="warning">
                        <h3 class="mb-0">
                            <b>{{ result.errors.length }}</b> items couldn't be cleared
                        </h3>
                    </BAlert>
                </div>

                <GTable
                    v-if="result.hasSomeErrors"
                    :fields="errorFields"
                    :items="result.errors"
                    data-test-id="errors-table" />
            </div>
        </div>
    </BModal>
</template>
