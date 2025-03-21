<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faCheckCircle,
    faDownload,
    faExclamationCircle,
    faFileImport,
    faLink,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BButtonToolbar, BCard, BCollapse, BLink, BTable } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type ExportRecord } from "./models/exportRecordModel";

library.add(faCheckCircle, faDownload, faExclamationCircle, faFileImport, faLink, faSpinner);

interface Props {
    records: ExportRecord[];
}
const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onReimport", record: ExportRecord): void;
    (e: "onDownload", record: ExportRecord): void;
    (e: "onCopyDownloadLink", record: ExportRecord): void;
}>();

const fields = [
    { key: "elapsedTime", label: "已导出" },
    { key: "format", label: "格式" },
    { key: "expires", label: "过期时间" },
    { key: "isUpToDate", label: "最新", class: "text-center" },
    { key: "isReady", label: "已准备好", class: "text-center" },
    { key: "actions", label: "操作" },
];

const isExpanded = ref(false);

const title = computed(() => (isExpanded.value ? `隐藏旧的导出记录` : `显示旧的导出记录`));

async function reimportObject(record: ExportRecord) {
    emit("onReimport", record);
}

function downloadObject(record: ExportRecord) {
    emit("onDownload", record);
}

function copyDownloadLink(record: ExportRecord) {
    emit("onCopyDownloadLink", record);
}
</script>

<template>
    <div>
        <BLink
            :class="isExpanded ? null : 'collapsed'"
            :aria-expanded="isExpanded ? 'true' : 'false'"
            aria-controls="collapse-previous"
            @click="isExpanded = !isExpanded">
            {{ title }}
        </BLink>

        <BCollapse id="collapse-previous" v-model="isExpanded">
            <BCard>
                <BTable :items="props.records" :fields="fields">
                    <template v-slot:cell(elapsedTime)="row">
                        <span :title="row.item.date">{{ row.value }}</span>
                    </template>

                    <template v-slot:cell(format)="row">
                        <span>{{ row.item.modelStoreFormat }}</span>
                    </template>

                    <template v-slot:cell(expires)="row">
                        <span v-if="row.item.hasExpired">已过期</span>

                        <span v-else-if="row.item.expirationDate" :title="row.item.expirationDate">
                            {{ row.item.expirationElapsedTime }}
                        </span>

                        <span v-else>没有</span>
                    </template>

                    <template v-slot:cell(isUpToDate)="row">
                        <FontAwesomeIcon
                            v-if="row.item.isUpToDate"
                            :icon="faCheckCircle"
                            class="text-success"
                            title="此导出记录包含最新更改。" />
                        <FontAwesomeIcon
                            v-else
                            :icon="faExclamationCircle"
                            class="text-danger"
                            title="此导出记录已过时。如果您需要最新的更改，请考虑生成新的导出。" />
                    </template>

                    <template v-slot:cell(isReady)="row">
                        <FontAwesomeIcon
                            v-if="row.item.isReady"
                            :icon="faCheckCircle"
                            class="text-success"
                            title="已准备好下载或导入。" />
                        <FontAwesomeIcon
                            v-else-if="row.item.isPreparing"
                            :icon="faSpinner"
                            spin
                            class="text-info"
                            title="导出处理中..." />
                        <FontAwesomeIcon
                            v-else-if="row.item.hasExpired"
                            :icon="faExclamationCircle"
                            class="text-danger"
                            title="该导出已过期。" />
                        <FontAwesomeIcon
                            v-else
                            :icon="faExclamationCircle"
                            class="text-danger"
                            title="导出失败。" />
                    </template>

                    <template v-slot:cell(actions)="row">
                        <BButtonToolbar aria-label="操作">
                            <BButtonGroup>
                                <BButton
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canDownload"
                                    title="下载"
                                    @click="downloadObject(row.item)">
                                    <FontAwesomeIcon :icon="faDownload" />
                                </BButton>

                                <BButton
                                    v-if="row.item.canDownload"
                                    title="复制下载链接"
                                    @click.stop="copyDownloadLink(row.item)">
                                    <FontAwesomeIcon :icon="faLink" />
                                </BButton>

                                <BButton
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canReimport"
                                    title="重新导入"
                                    @click="reimportObject(row.item)">
                                    <FontAwesomeIcon :icon="faFileImport" />
                                </BButton>
                            </BButtonGroup>
                        </BButtonToolbar>
                    </template>
                </BTable>
            </BCard>
        </BCollapse>
    </div>
</template>