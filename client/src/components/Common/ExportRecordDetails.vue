<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faCheckCircle,
    faClock,
    faExclamationCircle,
    faExclamationTriangle,
    faLink,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed } from "vue";

import type { ColorVariant } from ".";
import { type ExportRecord } from "./models/exportRecordModel";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faCheckCircle, faClock, faExclamationCircle, faExclamationTriangle, faLink);

interface Props {
    record: ExportRecord;
    objectType: string;
    actionMessage?: string;
    actionMessageVariant?: ColorVariant;
}

const props = withDefaults(defineProps<Props>(), {
    actionMessage: undefined,
    actionMessageVariant: "info",
});

const emit = defineEmits<{
    (e: "onActionMessageDismissed"): void;
    (e: "onReimport", record: ExportRecord): void;
    (e: "onDownload", record: ExportRecord): void;
    (e: "onCopyDownloadLink", record: ExportRecord): void;
}>();

const title = computed(() => (props.record.isReady ? `已导出` : `导出已开始`));
const preparingMessage = computed(
    () => `正在准备导出。根据您的 ${props.objectType} 的大小，可能需要一些时间。`
);

async function reimportObject() {
    emit("onReimport", props.record);
}

function downloadObject() {
    emit("onDownload", props.record);
}

function copyDownloadLink() {
    emit("onCopyDownloadLink", props.record);
}

function onMessageDismissed() {
    emit("onActionMessageDismissed");
}
</script>

<template>
    <div class="export-record-details">
        <Heading size="sm">
            <b>{{ title }}</b> {{ props.record.elapsedTime }}
        </Heading>

        <p v-if="!props.record.isPreparing">
            格式: <b class="record-archive-format">{{ props.record.modelStoreFormat }}</b>
        </p>

        <span v-if="props.record.isPreparing">
            <LoadingSpan :message="preparingMessage" />
        </span>
        <div v-else>
            <div v-if="props.record.hasFailed">
                <FontAwesomeIcon
                    :icon="faExclamationCircle"
                    class="text-danger record-failed-icon"
                    title="导出失败" />

                <span>
                    导出过程中出现问题。请重试，如果问题仍然存在，请联系管理员。
                </span>

                <BAlert show variant="danger">{{ props.record.errorMessage }}</BAlert>
            </div>
            <div v-else-if="props.record.isUpToDate" title="最新">
                <FontAwesomeIcon :icon="faCheckCircle" class="text-success record-up-to-date-icon" />
                <span> 该导出记录包含最新的 {{ props.objectType }} 更改。 </span>
            </div>
            <div v-else>
                <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning record-outdated-icon" />
                <span>
                    该导出已经过时，包含 {{ props.objectType }} 的变更数据，时间为
                    {{ props.record.elapsedTime }}。
                </span>
            </div>

            <p v-if="props.record.canExpire" class="mt-3">
                <span v-if="props.record.hasExpired">
                    <FontAwesomeIcon :icon="faClock" class="text-danger record-expired-icon" />
                    此下载链接已过期。
                </span>
                <span v-else>
                    <FontAwesomeIcon :icon="faClock" class="text-warning record-expiration-warning-icon" />
                    此下载链接将在 {{ props.record.expirationElapsedTime }} 后过期。
                </span>
            </p>

            <div v-if="props.record.isReady">
                <p class="mt-3">您可以对这个 {{ props.objectType }} 导出执行以下操作：</p>

                <BAlert
                    v-if="props.actionMessage !== undefined"
                    :variant="props.actionMessageVariant"
                    show
                    fade
                    dismissible
                    @dismissed="onMessageDismissed">
                    {{ props.actionMessage }}
                </BAlert>
                <div v-else class="actions">
                    <BButton
                        v-if="props.record.canDownload"
                        class="record-download-btn"
                        variant="primary"
                        @click="downloadObject">
                        下载
                    </BButton>

                    <BButton
                        v-if="props.record.canDownload"
                        title="复制下载链接"
                        size="sm"
                        variant="link"
                        @click.stop="copyDownloadLink">
                        <FontAwesomeIcon :icon="faLink" />
                    </BButton>

                    <BButton
                        v-if="props.record.canReimport"
                        class="record-reimport-btn"
                        variant="primary"
                        @click="reimportObject">
                        重新导入
                    </BButton>
                </div>
            </div>
        </div>
    </div>
</template>