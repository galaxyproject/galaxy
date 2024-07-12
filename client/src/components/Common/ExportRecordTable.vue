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
    { key: "elapsedTime", label: "Exported" },
    { key: "format", label: "Format" },
    { key: "expires", label: "Expires" },
    { key: "isUpToDate", label: "Up to date", class: "text-center" },
    { key: "isReady", label: "Ready", class: "text-center" },
    { key: "actions", label: "Actions" },
];

const isExpanded = ref(false);

const title = computed(() => (isExpanded.value ? `Hide old export records` : `Show old export records`));

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
                        <span v-if="row.item.hasExpired">Expired</span>

                        <span v-else-if="row.item.expirationDate" :title="row.item.expirationDate">
                            {{ row.item.expirationElapsedTime }}
                        </span>

                        <span v-else>No</span>
                    </template>

                    <template v-slot:cell(isUpToDate)="row">
                        <FontAwesomeIcon
                            v-if="row.item.isUpToDate"
                            :icon="faCheckCircle"
                            class="text-success"
                            title="This export record contains the latest changes." />
                        <FontAwesomeIcon
                            v-else
                            :icon="faExclamationCircle"
                            class="text-danger"
                            title="This export record is outdated. Please consider generating a new export if you need the latest changes." />
                    </template>

                    <template v-slot:cell(isReady)="row">
                        <FontAwesomeIcon
                            v-if="row.item.isReady"
                            :icon="faCheckCircle"
                            class="text-success"
                            title="Ready to download or import." />
                        <FontAwesomeIcon
                            v-else-if="row.item.isPreparing"
                            :icon="faSpinner"
                            spin
                            class="text-info"
                            title="Exporting in progress..." />
                        <FontAwesomeIcon
                            v-else-if="row.item.hasExpired"
                            :icon="faExclamationCircle"
                            class="text-danger"
                            title="The export has expired." />
                        <FontAwesomeIcon
                            v-else
                            :icon="faExclamationCircle"
                            class="text-danger"
                            title="The export failed." />
                    </template>

                    <template v-slot:cell(actions)="row">
                        <BButtonToolbar aria-label="Actions">
                            <BButtonGroup>
                                <BButton
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canDownload"
                                    title="Download"
                                    @click="downloadObject(row.item)">
                                    <FontAwesomeIcon :icon="faDownload" />
                                </BButton>

                                <BButton
                                    v-if="row.item.canDownload"
                                    title="Copy Download Link"
                                    @click.stop="copyDownloadLink(row.item)">
                                    <FontAwesomeIcon :icon="faLink" />
                                </BButton>

                                <BButton
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canReimport"
                                    title="Reimport"
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
