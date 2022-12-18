<script setup lang="ts">
import localize from "@/utils/localization";
import { computed, ref } from "vue";
import type { CleanupResult } from "./model";

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
    } else if (props.result.isPartialSuccess) {
        message = localize("Sorry, some items couldn't be cleared");
    } else if (props.result.success) {
        message = localize("Congratulations!");
    }
    return message;
});

const errorFields = [
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
