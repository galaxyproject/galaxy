<script setup>
import { computed, ref } from "vue";
import { BCard, BButton, BButtonGroup, BButtonToolbar, BCollapse, BTable, BLink } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faExclamationCircle,
    faCheckCircle,
    faDownload,
    faFileImport,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";

library.add(faExclamationCircle, faCheckCircle, faDownload, faFileImport, faSpinner);

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
const title = computed(() => (isExpanded.value ? `Hide export records` : `Show export records`));

async function reimportObject(record) {
    emit("onReimport", record);
}

function downloadObject(record) {
    emit("onDownload", record);
}
</script>

<template>
    <div>
        <b-link
            :class="isExpanded ? null : 'collapsed'"
            :aria-expanded="isExpanded ? 'true' : 'false'"
            aria-controls="collapse-previous"
            @click="isExpanded = !isExpanded">
            {{ title }}
        </b-link>
        <b-collapse id="collapse-previous" v-model="isExpanded">
            <b-card>
                <b-table :items="props.records" :fields="fields">
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
                        <font-awesome-icon
                            v-if="row.item.isUpToDate"
                            icon="check-circle"
                            class="text-success"
                            title="This export record contains the latest changes." />
                        <font-awesome-icon
                            v-else
                            icon="exclamation-circle"
                            class="text-danger"
                            title="This export record is outdated. Please consider generating a new export if you need the latest changes." />
                    </template>
                    <template v-slot:cell(isReady)="row">
                        <font-awesome-icon
                            v-if="row.item.isReady"
                            icon="check-circle"
                            class="text-success"
                            title="Ready to download or import." />
                        <font-awesome-icon
                            v-else-if="row.item.isPreparing"
                            icon="spinner"
                            spin
                            class="text-info"
                            title="Exporting in progress..." />
                        <font-awesome-icon
                            v-else-if="row.item.hasExpired"
                            icon="exclamation-circle"
                            class="text-danger"
                            title="The export has expired." />
                        <font-awesome-icon
                            v-else
                            icon="exclamation-circle"
                            class="text-danger"
                            title="The export failed." />
                    </template>
                    <template v-slot:cell(actions)="row">
                        <b-button-toolbar aria-label="Actions">
                            <b-button-group>
                                <b-button
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canDownload"
                                    title="Download"
                                    @click="downloadObject(row.item)">
                                    <font-awesome-icon icon="download" />
                                </b-button>
                                <b-button
                                    v-b-tooltip.hover.bottom
                                    :disabled="!row.item.canReimport"
                                    title="Reimport"
                                    @click="reimportObject(row.item)">
                                    <font-awesome-icon icon="file-import" />
                                </b-button>
                            </b-button-group>
                        </b-button-toolbar>
                    </template>
                </b-table>
            </b-card>
        </b-collapse>
    </div>
</template>
