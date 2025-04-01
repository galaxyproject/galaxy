<script lang="ts" setup>
import { type ColDef, type ValueSetterParams } from "ag-grid-community";
import { BLink } from "bootstrap-vue";
import { computed, ref } from "vue";

import { GalaxyApi, type SampleSheetColumnDefinition, type SampleSheetColumnDefinitions } from "@/api";
import { downloadWorkbook, initialValue } from "@/components/Collections/sheet/workbooks";
import { useAgGrid } from "@/composables/useAgGrid";

type RemoteFiles = string[];
type InitialElements = RemoteFiles;

interface Props {
    columnDefinitions: SampleSheetColumnDefinitions;
    initialElements: InitialElements;
    height?: string;
    width?: string;
}

const props = withDefaults(defineProps<Props>(), {
    height: "500px",
    width: "576px",
});

function initializeRowData(rowData: Record<string, unknown>[]) {
    for (const initialElement of props.initialElements) {
        const row: Record<string, unknown> = { uri: initialElement };
        (props.columnDefinitions || []).forEach((colDef) => {
            row[colDef.name] = initialValue(colDef);
        });
        rowData.push(row);
    }
}

const rowData = ref<Record<string, unknown>[]>([]);

function initialize() {
    rowData.value.splice(0, rowData.value.length);
    initializeRowData(rowData.value);
}

// Example Row Data
// const rowData = ref([{ "replicate number": 1, treatment: "treatment1", "is control?": true }]);

const { gridApi, AgGridVue, onGridReady, theme } = useAgGrid(resize);

function resize() {
    if (gridApi.value) {
        gridApi.value.sizeColumnsToFit();
    }
}

function validate(value: string, columnDefinition: SampleSheetColumnDefinition): boolean {
    if (columnDefinition.restrictions && !columnDefinition.restrictions.includes(value)) {
        return false; // Invalid if not in restrictions
    }

    switch (columnDefinition.type) {
        case "int":
            return Number.isInteger(Number(value));
        case "float":
            return !isNaN(parseFloat(value));
        case "boolean":
            return value === "true" || value === "false";
        case "string":
        default:
            return true;
    }
}

function valueSetter(params: ValueSetterParams, columnDefinition: SampleSheetColumnDefinition): boolean {
    const value = params.newValue;
    if (validate(value, columnDefinition)) {
        params.data[params.colDef.field!] = value;
        return true;
    } else {
        return false;
    }
}

// Generate Column Definitions from Schema
function generateGridColumnDefs(columnDefinitions: SampleSheetColumnDefinitions): ColDef[] {
    const columns = [uriColumn()];
    (columnDefinitions || []).forEach((colDef) => {
        const baseDef: ColDef = {
            headerName: colDef.name,
            field: colDef.name,
            editable: true,
            cellEditorParams: {},
            valueSetter: (params) => {
                return valueSetter(params, colDef);
            },
        };

        // Restrictions: Add dropdown editor for string type with restrictions
        if (colDef.restrictions && colDef.type === "string") {
            baseDef.cellEditor = "agSelectCellEditor";
            baseDef.cellEditorParams = {
                values: colDef.restrictions,
            };
        }
        // Validators
        baseDef.cellEditorParams.validate = (value: string) => validate(value, colDef);
        columns.push(baseDef);
    });
    return columns;
}

function uriColumn(): ColDef {
    const baseDef: ColDef = {
        headerName: "URI",
        field: "uri",
        editable: false,
        cellEditorParams: {},
    };
    return baseDef;
}

// Column Definitions
const columnDefs = computed(() => {
    return generateGridColumnDefs(props.columnDefinitions);
});

// Default Column Properties
const defaultColDef = ref<ColDef>({
    editable: true,
    sortable: true,
    filter: true,
    resizable: true,
});

const style = computed(() => {
    return { width: props.width, height: props.height };
});

const isDragging = ref(false);
const isProcessingUpload = ref(false);
const uploadErrorMessage = ref<string | undefined>(undefined);

type ParsedRowT = { [key: string]: string | number | boolean };
type ParsedRowsT = ParsedRowT[];

function handleUploadedData(rows: ParsedRowsT) {
    const currentRowData = rowData.value;
    for (const index in rows) {
        const row = rows[index];
        if (row) {
            for (const columnDefinition of props.columnDefinitions || []) {
                const updatedValue = row[columnDefinition.name];
                if (updatedValue !== undefined) {
                    const currentRow = currentRowData[index];
                    if (currentRow) {
                        currentRow[columnDefinition.name] = updatedValue;
                    }
                }
            }
        }
    }
    if (gridApi.value) {
        const params = {
            force: true,
            suppressFlash: true,
        };
        gridApi.value!.refreshCells(params);
    }
}

const handleDrop = async (event: DragEvent) => {
    const file = event.dataTransfer?.files[0];
    if (!file || !file.name.endsWith(".xlsx")) {
        uploadErrorMessage.value = "Please drop a valid XLSX file.";
        return;
    }

    isDragging.value = false;
    isProcessingUpload.value = true;

    try {
        // Read and base64 encode the file
        const fileContent = await fileToBase64(file);
        const base64Content = fileContent.split(",")[1] as string;
        const parseBody = {
            column_definitions: props.columnDefinitions || [],
            content: base64Content,
        };
        const { data, error } = await GalaxyApi().POST("/api/sample_sheet_workbook/parse", {
            body: parseBody,
        });
        if (data) {
            console.log("handling...");
            handleUploadedData(data.rows);
        } else {
            console.log("IN ERRROR!!!");
            console.log(error);
            uploadErrorMessage.value = "There was an error processing the file.";
        }
    } catch (error) {
        console.error("Error uploading file:", error);
        uploadErrorMessage.value = "There was an error processing the file.";
    } finally {
        isProcessingUpload.value = false;
    }
};

const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = (error) => reject(error);
        reader.readAsDataURL(file);
    });

const rootClasses = computed(() => {
    const classes: string[] = [theme, "dropzone"];
    if (isDragging.value) {
        classes.push("highlight");
    }
    return classes;
});

function downloadSeededWorkbook() {
    const initialRows = [];
    for (const initialItem of props.initialElements) {
        initialRows.push([initialItem]);
    }
    downloadWorkbook(props.columnDefinitions, initialRows);
}

initialize();
</script>

<template>
    <div
        :class="rootClasses"
        :style="style"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false">
        <AgGridVue
            :row-data="rowData"
            :column-defs="columnDefs"
            :default-col-def="defaultColDef"
            :style="style"
            @gridReady="onGridReady" />
        <BLink @click="downloadSeededWorkbook">Download this as spreadsheet and fill it in outside of Galaxy.</BLink>
    </div>
</template>
