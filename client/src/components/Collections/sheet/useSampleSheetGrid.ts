import type { ColDef } from "ag-grid-community";
import { ref, watch } from "vue";

import type { DCESummary, SampleSheetColumnDefinition } from "@/api";
import type { SampleSheetColumnValueT } from "@/api/datasetCollections";

export const MODEL_OBJECT = Symbol("sample sheet model object");

export type UriRow = Record<string, unknown> & {
    url: string;
    url_1?: string;
    list_identifiers: string;
    [MODEL_OBJECT]?: never;
};

export type ModelObjectRow = Record<string, unknown> & { [MODEL_OBJECT]: DCESummary };

export type AgRowData = UriRow | ModelObjectRow;

export const SAMPLE_SHEET_GRID_STYLE = { width: "100%", height: "500px" };

/**
 * Grid rows rebuilt by `buildRows` whenever its reactive inputs change. Bind them to the grid with
 * `v-model` so cell edits replace `rowData` and anything computed from the rows sees them.
 */
export function useSampleSheetGrid(buildRows: () => AgRowData[]) {
    const rowData = ref<AgRowData[]>([]);
    watch(
        buildRows,
        (rows) => {
            rowData.value = rows;
        },
        { immediate: true },
    );
    return { rowData };
}

export function modelObjectIdentifierColumn(headerName: string): ColDef {
    return {
        headerName,
        colId: "model-object-identifier",
        editable: false,
        valueGetter: (params) => params.data[MODEL_OBJECT].element_identifier,
    };
}

export function toAgGridColumnDefinition(colDef: SampleSheetColumnDefinition): ColDef {
    const headerDescription = colDef.description || colDef.name;
    return {
        headerName: colDef.name,
        headerTooltip: headerDescription,
        headerClass: headerDescription != colDef.name ? "ag-grid-column-has-custom-header-description" : "",
        field: colDef.name,
    };
}

type ParsedCellValue = { valid: true; value: SampleSheetColumnValueT | null } | { valid: false };

const INVALID: ParsedCellValue = { valid: false };

function valid(value: SampleSheetColumnValueT | null): ParsedCellValue {
    return { valid: true, value };
}

/**
 * Validate a value entered in the grid and convert it to the column's type. Text and select editors
 * hand over strings; the editors the grid infers from typed initial values hand over numbers and booleans.
 */
export function parseSampleSheetValue(
    newValue: unknown,
    columnDefinition: SampleSheetColumnDefinition,
): ParsedCellValue {
    const text = newValue === null || newValue === undefined ? "" : String(newValue);
    if (
        text === "" &&
        columnDefinition.optional &&
        (columnDefinition.type !== "string" || columnDefinition.restrictions)
    ) {
        return valid(null);
    }
    if (columnDefinition.restrictions && !columnDefinition.restrictions.map(String).includes(text)) {
        return INVALID;
    }
    switch (columnDefinition.type) {
        case "int": {
            const value = Number(text);
            return text.trim() !== "" && Number.isInteger(value) ? valid(value) : INVALID;
        }
        case "float": {
            const value = Number(text);
            return text.trim() !== "" && Number.isFinite(value) ? valid(value) : INVALID;
        }
        case "boolean": {
            const lower = text.toLowerCase();
            return lower === "true" || lower === "false" ? valid(lower === "true") : INVALID;
        }
        case "element_identifier":
        case "string":
        default:
            return /^[\w\-_ ?]*$/.test(text) ? valid(text) : INVALID;
    }
}
