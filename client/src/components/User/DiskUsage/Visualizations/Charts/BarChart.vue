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
const selectedLegendLabel = ref<string | undefined>(undefined);
const legendItems = ref<{ id: string; label: string; color: string }[]>([]);
let currentView: View | undefined;

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
                      select: { type: "point", fields: ["id"] },
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
                    labelFontSize: 14,
                    ...(props.yAxisLabelExpr ? { labelExpr: props.yAxisLabelExpr } : {}),
                },
            },
            color: {
                field: "id",
                type: "nominal",
                sort: null,
                legend: null,
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

function updateLegendItems(view: View) {
    const colorScale = view.scale("color") as (value: string) => string;
    const data = view.data("data_0") as Record<string, string>[];
    const items: { id: string; label: string; color: string }[] = [];
    for (const d of data) {
        if (d.id && d.formattedValue) {
            items.push({ id: d.id, label: d.formattedValue, color: colorScale(d.id) });
        }
    }
    legendItems.value = items;
}

function onLegendItemClick(id: string) {
    if (!props.enableSelection || !currentView) {
        return;
    }
    const store = currentView.data("barSelection_store");
    const isSelected = store.some((s: any) => s.values?.[0] === id);
    currentView.data("barSelection_store", isSelected ? [] : [{ fields: [{ field: "id", type: "E" }], values: [id] }]);
    selectedLegendLabel.value = isSelected ? undefined : id;
    currentView.runAsync();
}

function onNewView(view: View) {
    currentView = view;
    updateLegendItems(view);
    if (!props.enableSelection) {
        return;
    }
    view.addSignalListener("barSelection", (_name: string, value: Record<string, unknown>) => {
        const selectedId = (value as { id?: string[] })?.id?.[0];
        if (selectedId) {
            const dataPoint = props.data.find((d) => d.id === selectedId);
            if (dataPoint && selectedDataPoint.value?.id === dataPoint.id) {
                selectedDataPoint.value = undefined;
                selectedLegendLabel.value = undefined;
            } else {
                selectedDataPoint.value = dataPoint;
                selectedLegendLabel.value = selectedId;
            }
        } else {
            selectedDataPoint.value = undefined;
            selectedLegendLabel.value = undefined;
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
                <div class="chart-with-legend">
                    <VegaWrapper :spec="vegaSpec" @new-view="onNewView" />
                    <div v-if="legendItems.length > 0" class="legend-container">
                        <div
                            v-for="item in legendItems"
                            :key="item.id"
                            class="legend-item"
                            :class="{ 'legend-item-dimmed': selectedLegendLabel && selectedLegendLabel !== item.id }"
                            :style="{ cursor: enableSelection ? 'pointer' : 'default' }"
                            @click="onLegendItemClick(item.id)">
                            <span class="legend-symbol" :style="{ backgroundColor: item.color }" />
                            <span class="legend-label">{{ item.label }}</span>
                        </div>
                    </div>
                </div>
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

.chart-with-legend {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}

.chart-with-legend > :first-child {
    flex: 1;
    min-width: 0;
}

.legend-container {
    flex-shrink: 0;
    max-height: 350px;
    max-width: 250px;
    overflow-y: auto;
    padding: 0.25rem 0;
}

.legend-item {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.2rem 0.5rem;
    font-size: 0.85rem;
}

.legend-item:hover .legend-label {
    text-decoration: underline;
}

.legend-item-dimmed {
    opacity: 0.5;
}

.legend-symbol {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

.legend-label {
    word-break: break-word;
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
