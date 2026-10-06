<script setup lang="ts">
import type { ColDef } from "ag-grid-community";
import { computed } from "vue";

import type { SampleSheetColumnDefinition } from "@/api";
import {
    type AgRowData,
    modelObjectIdentifierColumn,
    SAMPLE_SHEET_GRID_STYLE,
    toAgGridColumnDefinition,
    useSampleSheetGrid,
} from "@/components/Collections/sheet/useSampleSheetGrid";
import { useDetailedCollection } from "@/composables/datasetCollections";
import { useAgGrid } from "@/composables/useAgGrid";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    collectionId: string;
}

const props = defineProps<Props>();

const { collection, collectionLoadError } = useDetailedCollection(props);

const { AgGridVue, onGridReady, theme } = useAgGrid();

const columnDefinitions = computed(() => (collection.value?.column_definitions ?? []) as SampleSheetColumnDefinition[]);

const { rowData } = useSampleSheetGrid(() =>
    (collection.value?.elements ?? []).map((element) => {
        const row: AgRowData = { __model_object: element };
        columnDefinitions.value.forEach((colDef, colIndex) => {
            row[colDef.name] = element.columns ? element.columns[colIndex] : null;
        });
        return row;
    }),
);

const columnDefs = computed<ColDef[]>(() => [
    modelObjectIdentifierColumn("Identifier"),
    ...columnDefinitions.value.map(toAgGridColumnDefinition),
]);

const defaultColDef: ColDef = {
    editable: false,
    sortable: false,
    filter: true,
    resizable: true,
};
</script>

<template>
    <div>
        <GAlert v-if="collectionLoadError" variant="danger" show dismissible>
            {{ collectionLoadError }}
        </GAlert>
        <LoadingSpan v-else-if="!collection" />
        <div v-else :class="theme">
            <AgGridVue
                :row-data="rowData"
                :column-defs="columnDefs"
                :default-col-def="defaultColDef"
                :style="SAMPLE_SHEET_GRID_STYLE"
                @gridReady="onGridReady" />
        </div>
    </div>
</template>

<style scoped>
:deep(.ag-grid-column-has-custom-header-description) {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>
