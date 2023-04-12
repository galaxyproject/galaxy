<script setup lang="ts">
import { BCard } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import * as d3 from "d3";

import type { DataValuePoint } from ".";

type DataValueFormatter = (dataPoint?: DataValuePoint | null) => string;

interface PieChartProps {
    title: string;
    data: DataValuePoint[];
    description?: string;
    width?: number;
    height?: number;
    enableTooltips?: boolean;
    enableSelection?: boolean;
    labelFormatter?: DataValueFormatter;
}

const props = withDefaults(defineProps<PieChartProps>(), {
    description: undefined,
    width: 400,
    height: 400,
    enableTooltips: true,
    enableSelection: false,
    labelFormatter: (dataPoint?: DataValuePoint | null) =>
        dataPoint ? `${dataPoint.label}: ${dataPoint.value}` : "No data",
});

const emit = defineEmits<{
    (e: "show-tooltip", dataPoint: DataValuePoint, mouseX: number, mouseY: number): void;
    (e: "hide-tooltip"): void;
    (e: "selection-changed", dataPoint?: DataValuePoint): void;
}>();

const pieChart = ref(null);
const legend = ref(null);
const chartTooltip = ref<HTMLBaseElement | null>(null);
const tooltipDataPoint = ref<DataValuePoint | null>(null);
const selectedDataPoint = ref<DataValuePoint | undefined>(undefined);
const chartArcs = ref<d3.Selection<SVGGElement, d3.PieArcDatum<DataValuePoint>, SVGGElement, unknown> | null>(null);
const legendEntries = ref<d3.Selection<SVGGElement | d3.BaseType, DataValuePoint, SVGGElement, unknown> | null>(null);

const total = computed(() => props.data.reduce((total, dataPoint) => total + dataPoint.value, 0));
const showTooltip = computed(() => props.enableTooltips && tooltipDataPoint.value !== null);
const hasData = computed(
    () => props.data.length > 0 && props.data.reduce((total, dataPoint) => total + dataPoint.value, 0) > 0
);

onMounted(() => {
    renderPieChart();
});

watch(
    () => props.data,
    () => {
        clearChart();
        renderPieChart();
    }
);

function renderPieChart() {
    chartArcs.value = drawChart();
    legendEntries.value = createLegend();
    setupEvents();
}

function clearChart() {
    d3.select(pieChart.value).selectAll("*").remove();
    d3.select(legend.value).selectAll("*").remove();
}

const color = d3.scaleOrdinal(d3.schemeCategory10);

function drawChart() {
    const data = props.data;
    const width = props.width;
    const height = props.height;

    const radius = height / 2.2;

    const svg = d3
        .select(pieChart.value)
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${width / 2},${height / 2})`);

    const pie = d3.pie<DataValuePoint>().value(applyThresholdToValue);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);

    const arcs = svg.selectAll("arc").data(pie(data)).enter().append("g").attr("class", "arc");

    arcs.append("path")
        // @ts-ignore
        .attr("d", arc)
        .attr("fill", (d) => entryColor(d.data));

    return arcs;
}

function createLegend() {
    const data = props.data;
    const topMargin = 10;
    const entrySpacing = 18;
    const entryRadius = 5;
    const labelOffset = 4;
    const baselineOffset = 4;

    const height = topMargin + data.length * entrySpacing + 50;
    const container = d3
        .select(legend.value)
        .append("svg")
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(0,${topMargin})`);

    const entries = container
        .selectAll("g")
        .data(data)
        .join("g")
        .attr("transform", (d, i) => `translate(0,${topMargin + i * entrySpacing})`);

    entries
        .append("circle")
        .attr("cx", entryRadius)
        .attr("r", entryRadius)
        .attr("fill", (d) => entryColor(d));

    entries
        .append("text")
        .attr("x", 2 * entryRadius + labelOffset)
        .attr("y", baselineOffset)
        .attr("fill", "black")
        .attr("font-size", "14px")
        .text((d) => props.labelFormatter(d));

    return entries;
}

function setupEvents() {
    if (props.enableTooltips) {
        setupTooltipEvents();
    }

    if (props.enableSelection) {
        setupSelectionEvents();
    }
}

function setupTooltipEvents() {
    chartArcs.value
        ?.on("mouseenter", (event, d) => {
            tooltipDataPoint.value = d.data;
            emit("show-tooltip", d.data, event.pageX, event.pageY);
        })
        .on("mousemove", (event) => {
            // Correct the page coordinates to compensate for scrolling offset
            const correctedX = event.pageX - window.pageXOffset;
            const correctedY = event.pageY - window.pageYOffset;
            setTooltipPosition(correctedX, correctedY);
        })
        .on("mouseleave", () => {
            tooltipDataPoint.value = null;
            emit("hide-tooltip");
        });
}

function setupSelectionEvents() {
    chartArcs.value?.on("click", (event, d) => {
        event.stopPropagation();
        toggleSelection(d.data);
    });
    legendEntries.value?.on("click", (event, d) => {
        event.stopPropagation();
        toggleSelection(d);
    });

    // Cancel selection on click anywhere else
    d3.select("body").on("click", () => {
        if (selectedDataPoint.value) {
            toggleSelection(selectedDataPoint.value);
        }
    });
}

function toggleSelection(dataPoint: DataValuePoint): void {
    if (selectedDataPoint.value === dataPoint) {
        selectedDataPoint.value = undefined;
    } else {
        selectedDataPoint.value = dataPoint;
    }
    highlightSelected();
    emit("selection-changed", selectedDataPoint.value);
}

function highlightSelected(): void {
    if (!chartArcs.value) {
        return;
    }

    chartArcs.value
        .selectAll<d3.BaseType, d3.PieArcDatum<DataValuePoint>>("path")
        .transition()
        .duration(200)
        .attr("opacity", (d) =>
            selectedDataPoint.value === undefined || d.data === selectedDataPoint.value ? 1.0 : 0.5
        );

    legendEntries.value
        ?.selectAll<d3.BaseType, DataValuePoint>("*")
        .transition()
        .duration(200)
        .attr("opacity", (d) => (selectedDataPoint.value === undefined || d === selectedDataPoint.value ? 1.0 : 0.5));
}

function entryColor(d: DataValuePoint): string {
    return color(`${d.id}`);
}

function setTooltipPosition(mouseX: number, mouseY: number): void {
    if (chartTooltip.value) {
        chartTooltip.value.style.left = `${mouseX}px`;
        chartTooltip.value.style.top = `${mouseY}px`;
    }
}

function applyThresholdToValue(d: DataValuePoint): number {
    // This is required to avoid a bug in d3 where it will not render the chart if the percentage of a slice is too small
    const percentage = (d.value / total.value) * 100;
    return percentage < 0.1 ? 0.1 : percentage;
}
</script>

<template>
    <b-card class="mb-3 mx-3">
        <template v-slot:header>
            <h3 class="text-center my-1">
                <b>{{ title }}</b>
            </h3>
        </template>
        <div v-if="hasData">
            <p class="text-center">{{ description }}</p>
            <div class="chart-area">
                <div ref="pieChart" class="pie-chart"></div>
                <div ref="legend" class="legend"></div>
                <div v-if="selectedDataPoint" class="selection-info">
                    <slot name="selection" :data="selectedDataPoint">
                        Selected: <b>{{ selectedDataPoint.label }}</b>
                    </slot>
                </div>
            </div>
        </div>
        <div v-else class="text-center">
            <p class="text-muted">No data to display. Populate some histories with datasets and come back.</p>
        </div>
        <div v-show="showTooltip" ref="chartTooltip" class="chart-tooltip">
            <slot name="tooltip" :data="tooltipDataPoint">
                <div>{{ labelFormatter(tooltipDataPoint) }}</div>
            </slot>
        </div>
    </b-card>
</template>

<style lang="css" scoped>
.chart-area {
    display: flex;
    justify-content: center;
}
.pie-chart {
    float: right;
}

.pie-chart .arc {
    cursor: pointer;
}

.legend {
    float: left;
}

.chart-tooltip {
    position: fixed;
    background-color: #fff;
    border: 1px solid #000;
    border-radius: 5px;
    padding: 5px;
    margin: 0 0 0 20px;
    z-index: 100;
    text-align: center;
    pointer-events: none;
}

.selection-info {
    background-color: #fff;
    border: 1px solid #000;
    border-radius: 5px;
    padding: 5px;
    z-index: 100;
    display: block;
    float: right;
    position: absolute;
    bottom: 0;
    right: 0;
    margin-bottom: 2rem;
    margin-right: 2rem;
    text-align: left;
    max-width: 300px;
}
</style>
