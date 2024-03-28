<script setup lang="ts">
import { BCard } from "bootstrap-vue";
import * as d3 from "d3";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import type { DataValuePoint } from ".";

interface BarChartProps {
    data: DataValuePoint[];
    title?: string;
    description?: string;
    width?: number;
    height?: number;
    enableTooltips?: boolean;
    enableSelection?: boolean;
    labelFormatter?: (dataPoint?: DataValuePoint | null) => string;
    valueFormatter?: (value: number) => string;
}

const props = withDefaults(defineProps<BarChartProps>(), {
    title: "Bar Chart",
    description: undefined,
    width: 720,
    height: 400,
    enableTooltips: true,
    enableSelection: false,
    labelFormatter: (dataPoint?: DataValuePoint | null) =>
        dataPoint ? `${dataPoint.label}: ${dataPoint.value}` : "No data",
    valueFormatter: (value: number) => `${value}`,
});

const emit = defineEmits<{
    (e: "show-tooltip", dataPoint: DataValuePoint, mouseX: number, mouseY: number): void;
    (e: "hide-tooltip"): void;
    (e: "selection-changed", dataPoint?: DataValuePoint): void;
}>();

const barChart = ref(null);
const legend = ref(null);
const chartTooltip = ref<HTMLBaseElement | null>(null);
const tooltipDataPoint = ref<DataValuePoint | null>(null);
const selectedDataPoint = ref<DataValuePoint | undefined>(undefined);
const chartBars = ref<d3.Selection<SVGRectElement, DataValuePoint, SVGGElement, unknown> | null>(null);
const legendEntries = ref<d3.Selection<SVGGElement | d3.BaseType, DataValuePoint, SVGGElement, unknown> | null>(null);

const showTooltip = computed(() => props.enableTooltips && tooltipDataPoint.value !== null);
const hasData = computed(
    () => props.data.length > 0 && props.data.reduce((total, dataPoint) => total + dataPoint.value, 0) > 0
);

onMounted(() => {
    renderBarChart();
});

watch(
    () => [
        props.data,
        props.width,
        props.height,
        props.enableTooltips,
        props.enableSelection,
        props.labelFormatter,
        props.valueFormatter,
    ],
    () => {
        // make sure v-if to conditionally display the div we're rendering this in
        // is available in the DOM before actually doing the rendering. Without
        // nextTick you cannot go from empty data -> chart when tweaking filtering
        // parameters.
        nextTick(() => {
            clearChart();
            renderBarChart();
        });
    }
);

function renderBarChart() {
    chartBars.value = drawChart();
    legendEntries.value = createLegend();
    setupEvents();
}

function clearChart() {
    d3.select(barChart.value).selectAll("*").remove();
    d3.select(legend.value).selectAll("*").remove();
}

const color = d3.scaleOrdinal(d3.schemeCategory10);

function drawChart() {
    const yAxisWidth = 70;
    const xAxisHeight = 5;
    const data = props.data;
    const chartWidth = props.width - yAxisWidth;
    const chartHeight = props.height;
    const chartXStart = yAxisWidth;
    const tickFontSize = 14;

    const svg = d3.select(barChart.value).append("svg").attr("width", props.width).attr("height", props.height);

    const g = svg.append("g").attr("transform", `translate(${chartXStart}, 0)`);

    const xScale = d3
        .scaleBand()
        .range([0, chartWidth - chartXStart])
        .domain(
            data.map(function (d) {
                return d.id;
            })
        )
        .padding(0.1);

    const xAxis = d3
        .axisBottom(xScale)
        .tickSize(0)
        .tickFormat(() => "");

    const yScale = d3
        .scaleLinear()
        .range([chartHeight - xAxisHeight, 0])
        .domain([0, d3.max(data, (d) => d.value) || 0]);

    const yAxis = d3
        .axisLeft<number>(yScale)
        .scale(yScale)
        .tickFormat(function (d) {
            return props.valueFormatter(d);
        })
        .ticks(5)
        .tickSizeInner(5)
        .tickSizeOuter(0);

    g.append("g")
        .attr("class", "axis")
        .attr("transform", "translate(0," + (chartHeight - xAxisHeight) + ")")
        .call(xAxis);

    g.append("g").attr("class", "axis").call(yAxis);

    g.selectAll(".tick text").style("font-size", `${tickFontSize}px`);

    const bars = g
        .selectAll(".bar")
        .data(data)
        .enter()
        .append("rect")
        .classed("bar", true)
        .attr("x", (d) => xScale(d.id) || 0)
        .attr("y", (d) => yScale(d.value) - xAxisHeight)
        .attr("width", xScale.bandwidth())
        .attr("height", (d) => chartHeight - yScale(d.value))
        .attr("fill", (d) => entryColor(d));

    return bars;
}

function createLegend() {
    const data = props.data;
    const topMargin = 10;
    const entrySpacing = 18;
    const entryRadius = 5;
    const labelOffset = 4;
    const baselineOffset = 4;

    const height = topMargin + data.length * entrySpacing;
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
        .classed("legend-item", true)
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
        .text((d) => props.labelFormatter(d));

    // Set the width of the SVG to the width of the widest entry
    let maxWidth = 0;
    for (const node of entries.nodes()) {
        const width = (node as HTMLElement).getBoundingClientRect().width;
        maxWidth = Math.max(maxWidth, width);
    }
    const svg = container.node()?.closest("svg");
    if (svg) {
        svg.setAttribute("width", `${maxWidth}`);
    }

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
    chartBars.value
        ?.on("mouseenter", (event: MouseEvent, d) => {
            tooltipDataPoint.value = d;
            emit("show-tooltip", d, event.pageX, event.pageY);
        })
        .on("mousemove", (event: MouseEvent) => {
            // Correct the page coordinates to compensate for scrolling offset
            const correctedX = event.pageX - window.scrollX;
            const correctedY = event.pageY - window.scrollY;
            setTooltipPosition(correctedX, correctedY);
        })
        .on("mouseleave", () => {
            tooltipDataPoint.value = null;
            emit("hide-tooltip");
        });
}

function setupSelectionEvents() {
    chartBars.value?.classed("clickable", true);
    chartBars.value?.on("click", (event, d) => {
        event.stopPropagation();
        toggleSelection(d);
    });

    legendEntries.value?.classed("clickable", true);
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
    if (!chartBars.value) {
        return;
    }

    chartBars.value
        .transition()
        .duration(200)
        .attr("opacity", (d) => (selectedDataPoint.value === undefined || d === selectedDataPoint.value ? 1.0 : 0.5));

    legendEntries.value
        ?.selectAll<d3.BaseType, DataValuePoint>("*")
        .transition()
        .duration(200)
        .attr("opacity", (d) => (selectedDataPoint.value === undefined || d === selectedDataPoint.value ? 1.0 : 0.5));
}

function entryColor(d: DataValuePoint): string {
    return color(`${d.id}`);
}

const tooltipMargin = 40;

function setTooltipPosition(mouseX: number, mouseY: number): void {
    const tooltip = chartTooltip.value;

    if (tooltip) {
        let x = mouseX;
        let y = mouseY;

        const width = tooltip.offsetWidth;
        const height = tooltip.offsetHeight;

        if (x + width + tooltipMargin > window.innerWidth) {
            x = window.innerWidth - width - tooltipMargin;
        }

        if (y + height + tooltipMargin > window.innerHeight) {
            y = window.innerHeight - height - tooltipMargin;
        }

        tooltip.style.left = `${x}px`;
        tooltip.style.top = `${y}px`;
    }
}
</script>

<template>
    <BCard class="mb-3">
        <template v-slot:header>
            <h3 class="text-center my-1">
                <slot name="title">
                    <b>{{ title }}</b>
                </slot>
            </h3>
        </template>
        <slot name="options" />
        <div v-if="hasData">
            <p class="chart-description">{{ description }}</p>
            <div class="chart-area">
                <div ref="barChart" class="bar-chart"></div>
                <div ref="legend" class="legend"></div>
                <div v-if="selectedDataPoint" class="selection-info">
                    <slot name="selection" :data="selectedDataPoint">
                        Selected: <b>{{ selectedDataPoint.label }}</b>
                    </slot>
                </div>
            </div>
        </div>
        <div v-else class="text-center">
            <p class="text-muted">No data to display. Populate some data and come back.</p>
        </div>
        <div v-show="showTooltip" ref="chartTooltip" class="chart-tooltip">
            <slot name="tooltip" :data="tooltipDataPoint">
                <div>{{ labelFormatter(tooltipDataPoint) }}</div>
            </slot>
        </div>
    </BCard>
</template>

<style lang="scss" scoped>
.chart-description {
    text-align: center;
    margin-bottom: 20px;
}

.chart-area {
    display: flex;
    justify-content: center;
}

.bar-chart {
    float: left;

    &:deep(svg) {
        overflow: visible;
    }

    &:deep(.bar.clickable) {
        cursor: pointer;
    }
}

.legend {
    float: right;
    height: 400px;
    overflow: auto;

    &:deep(.legend-item) {
        font-size: 14px;

        &.clickable {
            cursor: pointer;

            &:hover {
                text-decoration: underline;
            }
        }
    }
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
