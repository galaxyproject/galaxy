<script setup lang="ts">
import { BCard } from "bootstrap-vue";
import { onMounted, ref, computed } from "vue";
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
    labelFormatter?: DataValueFormatter;
}

const props = withDefaults(defineProps<PieChartProps>(), {
    description: undefined,
    width: 400,
    height: 400,
    enableTooltips: true,
    labelFormatter: (dataPoint?: DataValuePoint | null) =>
        dataPoint ? `${dataPoint.label}: ${dataPoint.value}` : "No data",
});

const emit = defineEmits<{
    (e: "show-tooltip", dataPoint: DataValuePoint, mouseX: number, mouseY: number): void;
    (e: "hide-tooltip"): void;
}>();

const pieChart = ref(null);
const legend = ref(null);
const chartTooltip = ref<HTMLBaseElement | null>(null);
const tooltipDataPoint = ref<DataValuePoint | null>(null);

const showTooltip = computed(() => props.enableTooltips && tooltipDataPoint.value !== null);

const hasData = computed(
    () => props.data.length > 0 && props.data.reduce((total, dataPoint) => total + dataPoint.value, 0) > 0
);

onMounted(() => {
    drawChart();
    createLegend();
});

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

    const pie = d3.pie<DataValuePoint>().value((d) => d.value);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);

    const arcs = svg.selectAll("arc").data(pie(data)).enter().append("g").attr("class", "arc");

    arcs.append("path")
        // @ts-ignore
        .attr("d", arc)
        // @ts-ignore
        .attr("fill", entryColor);

    setupTooltipEvents(arcs);
}

function createLegend() {
    const data = props.data;
    const titlePadding = 20;
    const entrySpacing = 18;
    const entryRadius = 5;
    const labelOffset = 4;
    const baselineOffset = 4;

    const height = titlePadding + data.length * entrySpacing + 50;
    const container = d3
        .select(legend.value)
        .append("svg")
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(0,${titlePadding})`);

    container
        .append("text")
        .attr("x", 0)
        .attr("y", 0)
        .attr("fill", "black")
        .attr("font-weight", "bold")
        .attr("font-size", "16px")
        .text("Legend");

    const entries = container
        .selectAll("g")
        .data(data)
        .join("g")
        .attr("transform", (d) => `translate(0, ${titlePadding + d.index * entrySpacing})`);

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
}

function entryColor(d: DataValuePoint): string {
    return color(`${d.index}`);
}

function setTooltipPosition(mouseX: number, mouseY: number): void {
    if (chartTooltip.value) {
        chartTooltip.value.style.left = `${mouseX}px`;
        chartTooltip.value.style.top = `${mouseY}px`;
    }
}

function setupTooltipEvents(arcs: d3.Selection<SVGGElement, d3.PieArcDatum<DataValuePoint>, SVGGElement, unknown>) {
    if (!props.enableTooltips) {
        return;
    }
    arcs.on("mouseenter", (event, d) => {
        tooltipDataPoint.value = d.data;
        emit("show-tooltip", d.data, event.pageX, event.pageY);
    })
        .on("mousemove", (event, d) => {
            setTooltipPosition(event.pageX, event.pageY);
        })
        .on("mouseleave", () => {
            tooltipDataPoint.value = null;
            emit("hide-tooltip");
        });
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
            <div class="chartArea">
                <div ref="pieChart" class="pieChart"></div>
                <div ref="legend" class="legend"></div>
            </div>
        </div>
        <div v-else class="text-center">
            <p class="text-muted">No data to display. Populate some histories with datasets and come back.</p>
        </div>
        <div v-show="showTooltip" ref="chartTooltip" class="chartTooltip">
            <slot name="tooltip" :data="tooltipDataPoint">
                <div>{{ labelFormatter(tooltipDataPoint) }}</div>
            </slot>
        </div>
    </b-card>
</template>

<style lang="css" scoped>
.chartArea {
    display: flex;
    justify-content: center;
}
.pieChart {
    float: right;
}

.legend {
    float: left;
}

.chartTooltip {
    position: fixed;
    background-color: #fff;
    border: 1px solid #000;
    border-radius: 5px;
    padding: 5px;
    margin: 0 0 0 20px;
    z-index: 100;
    text-align: center;
}
</style>
