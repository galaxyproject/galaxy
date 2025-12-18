import type { ColDef } from "ag-grid-community";
import { computed, ref } from "vue";

import type { SampleSheetColumnDefinition } from "@/api";

// Example Row Data
// const rowData = ref([{ "replicate number": 1, treatment: "treatment1", "is control?": true }]);
export type AgRowData = Record<string, unknown>;

export function buildsSampleSheetGrid(initializeRowData: (rowData: AgRowData[]) => void) {
    const rowData = ref<AgRowData[]>([]);

    const sampleSheetStyle = computed(() => {
        return { width: "100%", height: "500px" };
    });

    function initialize() {
        rowData.value.splice(0, rowData.value.length);
        initializeRowData(rowData.value);
    }

    return {
        initialize,
        rowData,
        sampleSheetStyle,
    };
}

export function toAgGridColumnDefinition(colDef: SampleSheetColumnDefinition): ColDef {
    const headerDescription = colDef.description || colDef.name;
    const hasCustomHeaderDescription = headerDescription != colDef.name;
    let headerClass = "";
    if (hasCustomHeaderDescription) {
        headerClass = "ag-grid-column-has-custom-header-description";
    }
    const baseDef: ColDef = {
        headerName: colDef.name,
        headerTooltip: colDef.description || colDef.name,
        headerClass,
        field: colDef.name,
        cellEditorParams: {},
    };
    return baseDef;
}
