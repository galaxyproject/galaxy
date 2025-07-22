<script setup lang="ts">
import {
    faCheckCircle,
    faDownload,
    faExclamationCircle,
    faFileImport,
    faLink,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BTable } from "bootstrap-vue";

import type { ExportRecord } from "./models/exportRecordModel";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

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
            <FontAwesomeIcon v-else :icon="faExclamationCircle" class="text-danger" title="The export failed." />
        </template>

        <template v-slot:cell(actions)="row">
            <GButtonGroup aria-label="Actions">
                <GButton
                    tooltip
                    tooltip-placement="bottom"
                    :disabled="!row.item.canDownload"
                    title="Download"
                    @click="downloadObject(row.item)">
                    <FontAwesomeIcon :icon="faDownload" />
                </GButton>

                <GButton
                    v-if="row.item.canDownload"
                    tooltip
                    tooltip-placement="bottom"
                    title="Copy Download Link"
                    @click.stop="copyDownloadLink(row.item)">
                    <FontAwesomeIcon :icon="faLink" />
                </GButton>

                <GButton
                    tooltip
                    tooltip-placement="bottom"
                    :disabled="!row.item.canReimport"
                    title="Reimport"
                    @click="reimportObject(row.item)">
                    <FontAwesomeIcon :icon="faFileImport" />
                </GButton>
            </GButtonGroup>
        </template>
    </BTable>
</template>
