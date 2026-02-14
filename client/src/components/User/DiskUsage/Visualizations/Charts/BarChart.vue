<script setup lang="ts">
import { BCard } from "bootstrap-vue";
import type { View } from "vega";
import type { VisualizationSpec } from "vega-embed";
import { computed, ref, watch } from "vue";

import type { DataValuePoint } from ".";

import GCard from "@/components/Common/GCard.vue";
import VegaWrapper from "@/components/Common/VegaWrapper.vue";

interface BarChartProps {
    data: DataValuePoint[];
    title?: string;
    description?: string;
    enableSelection?: boolean;
    labelFormatter?: (dataPoint?: DataValuePoint | null) => string;
    yAxisLabelExpr?: string;
}

const props = withDefaults(defineProps<BarChartProps>(), {
    title: "Bar Chart",
    description: undefined,
    enableSelection: false,
    yAxisLabelExpr: undefined,
    labelFormatter: (dataPoint?: DataValuePoint | null) =>
        dataPoint ? `${dataPoint.label}: ${dataPoint.value}` : "No data",
});

const emit = defineEmits<{
    (e: "selection-changed", dataPoint?: DataValuePoint): void;
}>();

const selectedDataPoint = ref<DataValuePoint | undefined>(undefined);

const hasData = computed(
    () => props.data.length > 0 && props.data.reduce((total, dataPoint) => total + dataPoint.value, 0) > 0,
);

const chartData = computed(() =>
    props.data.map((d) => ({
        ...d,
        formattedValue: props.labelFormatter(d),
    })),
);

const vegaSpec = computed<VisualizationSpec>(() => {
    const spec: VisualizationSpec = {
        $schema: "https://vega.github.io/schema/vega-lite/v5.json",
        data: { values: chartData.value },
        width: "container",
        height: 350,
        mark: { type: "bar", cursor: props.enableSelection ? "pointer" : "default" },
        params: props.enableSelection
            ? [
                  {
                      name: "barSelection",
                      select: { type: "point", fields: ["formattedValue"] },
                  },
              ]
            : [],
        encoding: {
            x: {
                field: "id",
                type: "nominal",
                axis: { labels: false, title: null, ticks: false },
                sort: null,
            },
            y: {
                field: "value",
                type: "quantitative",
                axis: {
                    title: null,
                    tickCount: 5,
                    ...(props.yAxisLabelExpr ? { labelExpr: props.yAxisLabelExpr } : {}),
                },
            },
            color: {
                field: "formattedValue",
                type: "nominal",
                sort: null,
                legend: { title: null, orient: "right", symbolType: "circle" },
            },
            opacity: props.enableSelection
                ? {
                      condition: { param: "barSelection", value: 1, empty: true },
                      value: 0.5,
                  }
                : { value: 1 },
            tooltip: [{ field: "formattedValue", type: "nominal", title: "Details" }],
        },
    };
    return spec;
});

watch(
    () => props.data,
    () => {
        if (selectedDataPoint.value) {
            const stillExists = props.data.some((d) => d.id === selectedDataPoint.value?.id);
            if (!stillExists) {
                selectedDataPoint.value = undefined;
                emit("selection-changed", undefined);
            }
        }
    },
);

function toggleLegendSelection(view: View, formattedValue: string) {
    const store = view.data("barSelection_store");
    const isSelected = store.some((s: any) => s.values?.[0] === formattedValue);
    view.data(
        "barSelection_store",
        isSelected ? [] : [{ fields: [{ field: "formattedValue", type: "E" }], values: [formattedValue] }],
    );
    view.runAsync();
}

let legendClickAbort: AbortController | undefined;

function addLegendClickTargets(view: View) {
    const container = view.container();
    if (!container) {
        return;
    }
    const entryGroup = container.querySelector(".role-legend-entry");
    if (!entryGroup) {
        return;
    }
    const data = view.data("data_0") as Record<string, string>[];
    const uniqueLabels: string[] = [];
    for (const d of data) {
        const fv = d.formattedValue;
        if (fv && !uniqueLabels.includes(fv)) {
            uniqueLabels.push(fv);
        }
    }
    entryGroup.querySelectorAll(".role-scope > g").forEach((entry, i) => {
        if (!uniqueLabels[i]) {
            return;
        }
        const bg = entry.querySelector(".background");
        if (!bg) {
            return;
        }
        const bbox = (bg as SVGPathElement).getBBox();
        const overlay = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        overlay.setAttribute("x", String(bbox.x));
        overlay.setAttribute("y", String(bbox.y));
        overlay.setAttribute("width", String(bbox.width));
        overlay.setAttribute("height", String(bbox.height));
        overlay.setAttribute("fill", "transparent");
        overlay.setAttribute("pointer-events", "all");
        overlay.setAttribute("cursor", "pointer");
        overlay.setAttribute("data-legend-index", String(i));
        entry.appendChild(overlay);
    });
    if (legendClickAbort) {
        legendClickAbort.abort();
    }
    legendClickAbort = new AbortController();
    container.addEventListener(
        "click",
        (e: MouseEvent) => {
            const target = (e.target as Element).closest("[data-legend-index]");
            if (!target) {
                return;
            }
            const index = parseInt(target.getAttribute("data-legend-index")!, 10);
            if (uniqueLabels[index]) {
                toggleLegendSelection(view, uniqueLabels[index]!);
            }
        },
        { signal: legendClickAbort.signal },
    );
}

function onNewView(view: View) {
    view.runAfter(() => {
        addLegendClickTargets(view);
    });
    if (!props.enableSelection) {
        return;
    }
    view.addSignalListener("barSelection", (_name: string, value: Record<string, unknown>) => {
        const selectedFV = (value as { formattedValue?: string[] })?.formattedValue?.[0];
        if (selectedFV) {
            const match = chartData.value.find((d) => d.formattedValue === selectedFV);
            const dataPoint = match ? props.data.find((d) => d.id === match.id) : undefined;
            if (dataPoint && selectedDataPoint.value?.id === dataPoint.id) {
                selectedDataPoint.value = undefined;
            } else {
                selectedDataPoint.value = dataPoint;
            }
        } else {
            selectedDataPoint.value = undefined;
        }
        emit("selection-changed", selectedDataPoint.value);
    });
}
</script>

<template>
    <BCard class="mb-3" header-class="p-0">
        <template v-slot:header>
            <h4 class="text-center my-1">
                <slot name="title">
                    <b>{{ title }}</b>
                </slot>
            </h4>
        </template>
        <slot name="options" />
        <div v-if="hasData">
            <p class="chart-description">{{ description }}</p>
            <div class="chart-area">
                <VegaWrapper :spec="vegaSpec" @new-view="onNewView" />
                <div v-if="selectedDataPoint" class="selection-info w-100">
                    <slot name="selection" :data="selectedDataPoint">
                        <GCard :title="`Selected: ${selectedDataPoint.label}`" />
                    </slot>
                </div>
            </div>
        </div>
        <div v-else class="text-center">
            <p class="text-muted">No data to display. Populate some data and come back.</p>
        </div>
    </BCard>
</template>

<style lang="scss" scoped>
.chart-description {
    text-align: center;
    margin-bottom: 20px;
}

.chart-area {
    position: relative;
}

.selection-info {
    z-index: 100;
    position: absolute;
    bottom: 0;
    right: 0;
    margin-bottom: 2rem;
    margin-right: 2rem;
    text-align: left;
    max-width: max(250px, 35%);
}
</style>
