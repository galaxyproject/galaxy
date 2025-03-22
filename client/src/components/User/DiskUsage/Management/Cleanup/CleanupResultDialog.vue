<script setup lang="ts">
import { computed, ref } from "vue";

import localize from "@/utils/localization";

import type { CleanupResult } from "./model";

import Alert from "components/Alert.vue";

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
    let message = localize("出现错误...");
    if (isLoading.value) {
        message = localize("正在释放空间...");
    } else if (props.result.isPartialSuccess) {
        message = localize("抱歉，部分项目无法清除");
    } else if (props.result.success) {
        message = localize("恭喜！");
    }
    return message;
});

const errorFields = [
    { key: "name", label: localize("名称") },
    { key: "reason", label: localize("原因") },
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
            <Alert
                variant="info"
                message="操作后，释放的存储空间仅针对唯一项目。这意味着某些项目可能不会释放任何存储空间，因为它们是其他项目的副本。" />
            <b-spinner v-if="isLoading" class="mx-auto" data-test-id="loading-spinner" />
            <div v-else>
                <b-alert v-if="result.hasFailed" show variant="danger" data-test-id="error-alert">
                    {{ result.errorMessage }}
                </b-alert>
                <h3 v-else-if="result.success" data-test-id="success-info">
                    您已清除 <b>{{ result.niceTotalFreeBytes }}</b>
                </h3>
                <div v-else-if="result.isPartialSuccess" data-test-id="partial-success-info">
                    <h3>
                        您已成功清除 <b>{{ result.totalCleaned }}</b> 个项目，共计
                        <b>{{ result.niceTotalFreeBytes }}</b>，但是...
                    </h3>
                    <b-alert v-if="result.hasSomeErrors" show variant="warning">
                        <h3 class="mb-0">
                            <b>{{ result.errors.length }}</b> 个项目无法清除
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

