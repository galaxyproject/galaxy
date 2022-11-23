<script setup>
import { computed, ref } from "vue";
import { BCard, BButton, BButtonGroup, BButtonToolbar, BCollapse, BTable } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationCircle, faCheckCircle, faDownload, faFileImport } from "@fortawesome/free-solid-svg-icons";

library.add(faExclamationCircle, faCheckCircle, faDownload, faFileImport);

const props = defineProps({
    records: {
        type: Array,
        required: true,
    },
});

const emit = defineEmits(["onReimport", "onDownload"]);

const fields = [
    { key: "elapsedTime", label: "Exported" },
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
        <b-button
            :class="isExpanded ? null : 'collapsed'"
            :aria-expanded="isExpanded ? 'true' : 'false'"
            aria-controls="collapse-previous"
            @click="isExpanded = !isExpanded">
            {{ title }}
        </b-button>
        <b-collapse id="collapse-previous" v-model="isExpanded">
            <b-card>
                <b-table :items="props.records" :fields="fields">
                    <template v-slot:cell(elapsedTime)="row">
                        <span :title="row.item.date">{{ row.value }}</span>
                    </template>
                    <template v-slot:cell(isUpToDate)="row">
                        <font-awesome-icon v-if="row.item.isUpToDate" icon="check-circle" class="text-success" />
                        <font-awesome-icon v-else icon="exclamation-circle" class="text-danger" />
                    </template>
                    <template v-slot:cell(isReady)="row">
                        <font-awesome-icon v-if="row.item.isReady" icon="check-circle" class="text-success" />
                        <font-awesome-icon v-else icon="exclamation-circle" class="text-danger" />
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
