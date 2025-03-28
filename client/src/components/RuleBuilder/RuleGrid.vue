<script lang="ts" setup>
import { useResizeObserver } from "@vueuse/core";
import { type ColDef, type IHeaderParams, type ValueGetterParams } from "ag-grid-community";
import { computed, ref, watch } from "vue";

import { useAgGrid } from "@/composables/useAgGrid";

interface Props {
    data: string[][];
    colHeaders: string[];
    height?: string;
}

const props = withDefaults(defineProps<Props>(), {
    height: "500px",
});

const agGrid = ref<HTMLDivElement | null>(null);
useResizeObserver(agGrid, () => {
    resize();
});

// Default Column Properties
const defaultColDef = ref<ColDef>({
    editable: false,
    sortable: false,
    filter: false,
    resizable: false, // we add columns automatically, best if this is just off right?
    suppressMovable: true,
});

const style = computed(() => {
    return { width: "100%", height: props.height };
});

const agColumnHeaders = computed(() => {
    return props.colHeaders.map((header: string, index: number) => {
        return {
            headerName: header,
            headerComponent: CustomHeader,
            valueGetter: (params: ValueGetterParams) => {
                return params.data[index];
            },
        };
    });
});

// Rule builder builds column headers with HTML (mix of b and i tags),
// this custom component renders HTML instead of text.
class CustomHeader {
    private eGui: HTMLElement | undefined;

    init(params: IHeaderParams) {
        this.eGui = document.createElement("div");
        this.eGui.style.cssText = "width: 100%; text-align: center";
        this.eGui.innerHTML = `${params.displayName}`;
    }

    getGui() {
        return this.eGui!;
    }

    refresh(params: IHeaderParams): boolean {
        return false;
    }
}

// this doesn't work but the idea is to increase the column widths to fill
// the horizontal space if they are too small after auto-sizing.
/*
function cleanUpColumnsIfNeeded() {
    if(columnApi.value) {
        const gridWidth = document.querySelector("#rules-ag-grid")?.clientWidth || 0;
        const totalColumnWidth = (columnApi.value.getAllColumns() || []).reduce(
            (sum: number, col: Column) => sum + (col.getActualWidth() || 0),
            0
        );
        if (totalColumnWidth < gridWidth && gridApi.value) {
            gridApi.value.sizeColumnsToFit();
        }
    }
}
*/

function resize() {
    if (columnApi.value) {
        columnApi.value.autoSizeAllColumns();
    }
}

const { columnApi, AgGridVue, onGridReady, resizeOnNextTick, theme } = useAgGrid(resize);

watch(() => props.colHeaders, resizeOnNextTick);
</script>

<template>
    <div :class="theme" :style="style">
        <AgGridVue
            id="rules-ag-grid"
            ref="agGrid"
            :rowData="data"
            :columnDefs="agColumnHeaders"
            :defaultColDef="defaultColDef"
            :style="style"
            :row-height="20"
            :header-height="30"
            :cell-selection="true"
            @gridReady="onGridReady" />
    </div>
</template>

<style>
/* Reduce padding and font size for compact rows */
.ag-theme-alpine .ag-row {
    font-size: 12px;
    line-height: 20px; /* Adjust line height to match rowHeight */
    padding: 2px 5px; /* Adjust padding */
}

/* Adjust header font size and padding */
.ag-theme-alpine .ag-header-cell-label {
    font-size: 13px;
    padding: 3px 5px;
}
</style>
