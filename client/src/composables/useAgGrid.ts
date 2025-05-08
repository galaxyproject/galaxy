import "ag-grid-community/styles/ag-grid.min.css";
import "ag-grid-community/styles/ag-theme-alpine.min.css";

import { type ColumnApi, type GridApi, type GridReadyEvent } from "ag-grid-community";
import { defineAsyncComponent, nextTick, ref } from "vue";

export function useAgGrid(forceGridSize: () => void) {
    const gridApi = ref<GridApi | null>(null);
    const columnApi = ref<ColumnApi | null>(null);
    const theme = "ag-theme-alpine";
    function resizeOnNextTick() {
        nextTick(forceGridSize);
    }

    function onGridReady(params: GridReadyEvent) {
        gridApi.value = params.api;
        columnApi.value = params.columnApi;
        forceGridSize();
    }

    const AgGridVue = defineAsyncComponent(async () => {
        const { AgGridVue } = await import(/* webpackChunkName: "agGrid" */ "ag-grid-vue");
        return AgGridVue;
    });

    return { AgGridVue, gridApi, columnApi, resizeOnNextTick, onGridReady, theme };
}
