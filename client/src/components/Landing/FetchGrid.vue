<script setup lang="ts">
import type { ColDef } from "ag-grid-community";
import { computed, ref, watch } from "vue";

import type { AnyFetchTarget, HdcaUploadTarget } from "@/api/tools";
import type { ParsedFetchWorkbookColumnType } from "@/components/Collections/wizard/types";
import type { CardAction } from "@/components/Common/GCard.types";
import { useAgGrid } from "@/composables/useAgGrid";

import { type DerivedColumn, type FetchTable, fetchTargetToTable, type RowsType, tableToRequest } from "./fetchModels";
import { enforceColumnUniqueness, useGridHelpers } from "./gridHelpers";

import GCard from "@/components/Common/GCard.vue";
import DataFetchRequestParameter from "@/components/JobParameters/DataFetchRequestParameter.vue";

interface Props {
    target: AnyFetchTarget;
}

const props = defineProps<Props>();

const { gridApi, AgGridVue, onGridReady, theme } = useAgGrid(resize);

function resize() {
    if (gridApi.value) {
        gridApi.value.sizeColumnsToFit();
    }
}

const style = computed(() => {
    return { width: "100%" };
});

type AgRowData = Record<string, unknown>;

const gridRowData = ref<AgRowData[]>([]);
const gridColumns = ref<ColDef[]>([]);
const richSupportForTarget = ref(false);
const modified = ref(false);
type ViewModeT = "table" | "raw";
const viewMode = ref<ViewModeT>("raw");

const collectionTarget = computed(() => {
    if (props.target.destination.type == "hdca") {
        return props.target as HdcaUploadTarget;
    } else {
        throw Error("Not a collection target - logic error");
    }
});

const { makeExtensionColumn, makeDbkeyColumn } = useGridHelpers();

const title = computed(() => {
    let title;
    if (props.target.destination.type == "hdas") {
        title = "Datasets";
    } else if (props.target.destination.type == "hdca") {
        title = `Collection: ${collectionTarget.value.name}`;
    } else {
        title = "Library";
    }
    if (modified.value) {
        title += " (modified)";
    }
    return title;
});

function initializeRowData(rowData: AgRowData[], rows: RowsType) {
    for (const row of rows) {
        rowData.push({ ...row });
    }
}

const BOOLEAN_COLUMNS: ParsedFetchWorkbookColumnType[] = [
    "to_posix_lines",
    "space_to_tab",
    "auto_decompress",
    "deferred",
];

function derivedColumnToAgColumnDefinition(column: DerivedColumn): ColDef {
    const colDef: ColDef = {
        headerName: column.title,
        field: column.key(),
        sortable: false,
        filter: false,
        resizable: true,
    };
    if (column.type === "file_type") {
        makeExtensionColumn(colDef);
    } else if (column.type === "dbkey") {
        makeDbkeyColumn(colDef);
    } else if (column.type == "list_identifiers" && collectionTypeRef.value?.indexOf(":") === -1) {
        // flat list-like structure - lets make sure element names are unique.
        enforceColumnUniqueness(colDef);
    } else if (BOOLEAN_COLUMNS.indexOf(column.type) >= 0) {
        colDef.cellRenderer = "agCheckboxCellRenderer";
        colDef.cellEditor = "agCheckboxCellEditor";
    }
    return colDef;
}

function initializeColumns(columns: DerivedColumn[]) {
    if (!columns || columns.length === 0) {
        gridColumns.value = [];
        return;
    }

    gridColumns.value = columns.map(derivedColumnToAgColumnDefinition);
}

const collectionTypeRef = ref<string | undefined>(undefined);
const columnsRef = ref<DerivedColumn[]>([]);
const autoDecompressRef = ref<boolean | undefined>(undefined);

function initializeTabularVersionOfTarget() {
    let table;
    try {
        table = fetchTargetToTable(props.target);
    } catch (error) {
        richSupportForTarget.value = false;
        return;
    }
    const { columns, rows, collectionType } = table;
    columnsRef.value = columns;
    collectionTypeRef.value = collectionType;
    autoDecompressRef.value = table.autoDecompress;
    initializeColumns(columns);
    gridRowData.value.splice(0, gridRowData.value.length);
    initializeRowData(gridRowData.value, rows);
    richSupportForTarget.value = true;
    viewMode.value = "table";
}

function initialize() {
    initializeTabularVersionOfTarget();
    modified.value = false;
}

// Default Column Properties
const defaultColDef = ref<ColDef>({
    editable: true,
    sortable: true,
    filter: true,
    resizable: true,
});

function asTarget(): AnyFetchTarget {
    if (modified.value) {
        const newTable: FetchTable = {
            columns: columnsRef.value,
            rows: gridRowData.value as RowsType,
            autoDecompress: autoDecompressRef.value,
            collectionType: collectionTypeRef.value,
            isCollection: collectionTypeRef.value !== undefined,
        };
        return tableToRequest(newTable);
    } else {
        return Object.assign({}, props.target);
    }
}

defineExpose({
    asTarget,
});

watch(
    () => {
        props.target;
    },
    () => {
        initialize();
        // is this block needed?
        if (gridApi.value) {
            const params = {
                force: true,
                suppressFlash: true,
            };
            gridApi.value!.refreshCells(params);
        }
    },
    {
        immediate: true,
    }
);

const viewRequestAction: CardAction = {
    id: "source",
    label: "View Request",
    title: "View raw data request JSON",
    handler: () => (viewMode.value = "raw"),
    visible: true,
};

const viewTableAction: CardAction = {
    id: "table",
    label: "View Table",
    title: "View data in table format",
    handler: () => (viewMode.value = "table"),
    visible: richSupportForTarget.value,
};

const secondaryActions = computed<CardAction[]>(() => {
    if (!richSupportForTarget.value) {
        return [];
    }

    const actions: CardAction[] = [];
    if (viewMode.value === "raw") {
        actions.push(viewTableAction);
    } else {
        actions.push(viewRequestAction);
    }
    return actions;
});

function handleDataUpdated(event: any) {
    modified.value = true;
}
</script>

<template>
    <GCard :title="title" :secondary-actions="secondaryActions">
        <template v-slot:description>
            <div v-if="viewMode === 'raw'">
                <BAlert v-if="!richSupportForTarget" show dismissible variant="warning">
                    This target is using advanced features that we don't yet support a rich tabular view for, an
                    annotated request is shown here and can still be used to import the target data. If you would like
                    this to see this kind of target supported, please
                    <a href="https://github.com/galaxyproject/galaxy/issues">create an issue on GitHub</a>
                    titled something like "Support Rich View of Data Fetch Request" and include this request as an
                    example.
                </BAlert>
                <BAlert v-if="modified" show dismissible variant="warning">
                    This shows the initial data import request, you have modified the import data and your modifications
                    will be reflected in the final data import but not in this initial request.
                </BAlert>
                <DataFetchRequestParameter :parameter-value="props.target" />
            </div>
            <div v-else-if="viewMode === 'table'" :class="[theme]">
                <BAlert v-if="modified" show dismissible variant="info">
                    You have modified the import data from the initial request, these modifications will be reflected in
                    the final data import.
                </BAlert>
                <AgGridVue
                    :row-data="gridRowData"
                    :column-defs="gridColumns"
                    :default-col-def="defaultColDef"
                    :style="style"
                    dom-layout="autoHeight"
                    @cellValueChanged="handleDataUpdated"
                    @gridReady="onGridReady" />
            </div>
        </template>
    </GCard>
</template>
