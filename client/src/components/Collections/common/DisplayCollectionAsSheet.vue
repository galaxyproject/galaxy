<script setup lang="ts">
import type { ColDef } from "ag-grid-community";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { SampleSheetColumnDefinitions } from "@/api";
import {
    type AgRowData,
    buildsSampleSheetGrid,
    toAgGridColumnDefinition,
} from "@/components/Collections/sheet/useSampleSheetGrid";
import { useDetailedCollection } from "@/composables/datasetCollections";
import { useAgGrid } from "@/composables/useAgGrid";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    collectionId: string;
}

const props = defineProps<Props>();

const { collection, collectionLoadError } = useDetailedCollection(props);

function initializeRowData(rowData: AgRowData[]) {
    const collectionDetailed = collection.value;
    if (collectionDetailed) {
        for (const element of collectionDetailed.elements) {
            const row: AgRowData = { __model_object: element };
            (collectionDetailed.column_definitions || []).forEach((colDef) => {
                // TODO:
                row[colDef.name] = "foobar";
            });
            rowData.push(row);
        }
    }

    return [];
}

const { rowData, initialize, sampleSheetStyle } = buildsSampleSheetGrid(initializeRowData);

const { gridApi, AgGridVue, onGridReady, theme } = useAgGrid(resize);

function resize() {
    if (gridApi.value) {
        gridApi.value.sizeColumnsToFit();
    }
}

// Generate Column Definitions from Schema
function generateGridColumnDefs(columnDefinitions: SampleSheetColumnDefinitions): ColDef[] {
    const columns: ColDef[] = [];
    columns.push({
        headerName: "Identifier",
        field: "__model_object",
        editable: false,
        cellEditorParams: {},
        valueFormatter: (params) => {
            return params.data.__model_object.element_identifier;
        },
    });
    (columnDefinitions || []).forEach((colDef) => {
        const baseDef = toAgGridColumnDefinition(colDef);
        columns.push(baseDef);
    });
    return columns;
}

// Column Definitions
const columnDefs = computed(() => {
    if (!collection.value || !collection.value.column_definitions) {
        return [];
    }
    return generateGridColumnDefs(collection.value.column_definitions as SampleSheetColumnDefinitions);
});

watch(
    () => collection.value,
    () => {
        initialize();
        resize();
    },
    { immediate: true },
);

// Default Column Properties
const defaultColDef = ref<ColDef>({
    editable: false,
    sortable: false,
    filter: true,
    resizable: true,
});
</script>

<template>
    <div>
        <LoadingSpan v-if="!collection" />
        <BAlert v-else-if="collectionLoadError" variant="danger" show dismissible>
            {{ collectionLoadError }}
        </BAlert>
        <div v-else>
            <div :class="theme">
                <AgGridVue
                    :row-data="rowData"
                    :column-defs="columnDefs"
                    :default-col-def="defaultColDef"
                    :style="sampleSheetStyle"
                    @gridReady="onGridReady" />
            </div>
        </div>
    </div>
</template>
