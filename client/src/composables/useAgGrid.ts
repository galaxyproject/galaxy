import "ag-grid-community/styles/ag-grid.min.css";
import "ag-grid-community/styles/ag-theme-alpine.min.css";

import type { GridApi, GridReadyEvent } from "ag-grid-community";
import { defineAsyncComponent, nextTick, ref } from "vue";

const AgGridVue = defineAsyncComponent(async () => (await import("ag-grid-vue3")).AgGridVue);

/** `forceGridSize` defaults to fitting the columns to the grid's width. */
export function useAgGrid(forceGridSize?: () => void) {
    const gridApi = ref<GridApi | null>(null);
    const theme = "ag-theme-alpine";

    const resize = forceGridSize ?? (() => gridApi.value?.sizeColumnsToFit());

    function resizeOnNextTick() {
        nextTick(resize);
    }

    function onGridReady(params: GridReadyEvent) {
        gridApi.value = params.api;
        resize();
    }

    return { AgGridVue, gridApi, resize, resizeOnNextTick, onGridReady, theme };
}
