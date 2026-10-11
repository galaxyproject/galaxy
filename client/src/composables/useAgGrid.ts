import "ag-grid-community/styles/ag-grid.min.css";
import "ag-grid-community/styles/ag-theme-alpine.min.css";

import type { GridApi, GridReadyEvent } from "ag-grid-community";
import { defineAsyncComponent, nextTick, ref } from "vue";

export function useAgGrid(forceGridSize: () => void) {
    const gridApi = ref<GridApi | null>(null);
    const theme = "ag-theme-alpine";
    function resizeOnNextTick() {
        nextTick(forceGridSize);
    }

    function onGridReady(params: GridReadyEvent) {
        gridApi.value = params.api;
        forceGridSize();
    }

    const AgGridVue = defineAsyncComponent(async () => {
        const { AgGridVue } = await import("ag-grid-vue3");
        return AgGridVue;
    });

    return { AgGridVue, gridApi, resizeOnNextTick, onGridReady, theme };
}
