<script setup>
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
import { BTable } from "bootstrap-vue";
import { computed, ref } from "vue";

import GButton from "@/component-library/GButton.vue";
import GButtonGroup from "@/component-library/GButtonGroup.vue";
import GButtonToolbar from "@/component-library/GButtonToolbar.vue";
import GCard from "@/component-library/GCard.vue";
import GCollapse from "@/component-library/GCollapse.vue";
import GLink from "@/component-library/GLink.vue";

library.add(faExclamationCircle, faCheckCircle, faDownload, faFileImport, faSpinner, faLink);

const props = defineProps({
    records: {
        type: Array,
        required: true,
    },
});

const emit = defineEmits(["onReimport", "onDownload"]);

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

async function reimportObject(record) {
    emit("onReimport", record);
}

function downloadObject(record) {
    emit("onDownload", record);
}

function copyDownloadLink(record) {
    emit("onCopyDownloadLink", record);
}
</script>

<template>
    <div>
        <GLink
            :class="isExpanded ? null : 'collapsed'"
            :aria-expanded="isExpanded ? 'true' : 'false'"
            aria-controls="collapse-previous"
            @click="isExpanded = !isExpanded">
            {{ title }}
        </GLink>
        <GCollapse id="collapse-previous" v-model="isExpanded">
            <GCard>
                <BTable :items="props.records" :fields="fields">
                    <template v-slot:cell(elapsedTime)="row">
                        <span :title="row.item.date">{{ row.value }}</span>
                    </template>
                    <template v-slot:cell(format)="row">
                        <span>{{ row.item.modelStoreFormat }}</span>
                    </template>
                    <template v-slot:cell(expires)="row">
                        <span v-if="row.item.hasExpired">Expired</span>
                        <span v-else-if="row.item.expirationDate" :title="row.item.expirationDate">{{
                            row.item.expirationElapsedTime
                        }}</span>
                        <span v-else>No</span>
                    </template>
                    <template v-slot:cell(isUpToDate)="row">
                        <FontAwesomeIcon
                            v-if="row.item.isUpToDate"
                            icon="check-circle"
                            class="text-success"
                            title="This export record contains the latest changes." />
                        <FontAwesomeIcon
                            v-else
                            icon="exclamation-circle"
                            class="text-danger"
                            title="This export record is outdated. Please consider generating a new export if you need the latest changes." />
                    </template>
                    <template v-slot:cell(isReady)="row">
                        <FontAwesomeIcon
                            v-if="row.item.isReady"
                            icon="check-circle"
                            class="text-success"
                            title="Ready to download or import." />
                        <FontAwesomeIcon
                            v-else-if="row.item.isPreparing"
                            icon="spinner"
                            spin
                            class="text-info"
                            title="Exporting in progress..." />
                        <FontAwesomeIcon
                            v-else-if="row.item.hasExpired"
                            icon="exclamation-circle"
                            class="text-danger"
                            title="The export has expired." />
                        <FontAwesomeIcon
                            v-else
                            icon="exclamation-circle"
                            class="text-danger"
                            title="The export failed." />
                    </template>
                    <template v-slot:cell(actions)="row">
                        <GButtonToolbar aria-label="Actions">
                            <GButtonGroup>
                                <GButton
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canDownload"
                                    title="Download"
                                    @click="downloadObject(row.item)">
                                    <FontAwesomeIcon icon="download" />
                                </GButton>
                                <GButton
                                    v-if="row.item.canDownload"
                                    title="Copy Download Link"
                                    @click.stop="copyDownloadLink(row.item)">
                                    <FontAwesomeIcon icon="link" />
                                </GButton>
                                <GButton
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canReimport"
                                    title="Reimport"
                                    @click="reimportObject(row.item)">
                                    <FontAwesomeIcon icon="file-import" />
                                </GButton>
                            </GButtonGroup>
                        </GButtonToolbar>
                    </template>
                </BTable>
            </GCard>
        </GCollapse>
    </div>
</template>