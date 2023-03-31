<script setup lang="ts">
import { onMounted, ref } from "vue";
import * as d3 from "d3";

import type { DataValuePoint } from ".";

interface PieChartProps {
    title: string;
    data: DataValuePoint[];
    width?: number;
    height?: number;
    labelFormatter?: (dataPoint: DataValuePoint) => string;
    tooltipFormatter?: (dataPoint: DataValuePoint) => string;
}

const props = withDefaults(defineProps<PieChartProps>(), {
    width: 1000,
    height: 400,
    labelFormatter: (dataPoint: DataValuePoint) => `${dataPoint.label}: ${dataPoint.value}`,
    tooltipFormatter: (dataPoint: DataValuePoint) => `${dataPoint.label}: ${dataPoint.value}`,
});

const chart = ref(null);

onMounted(() => {
    drawChart();
});

function drawChart() {
    const data = props.data;
    const width = props.width;
    const height = props.height;

    const radius = height / 2.2;

    const svg = d3
        .select(chart.value)
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${width / 2},${height / 2})`)
        .text(props.title);

    const color = d3.scaleOrdinal(d3.schemeCategory10);

    // @ts-ignore
    const pie = d3.pie().value((d) => d.value);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);

    // @ts-ignore
    const arcs = svg.selectAll("arc").data(pie(data)).enter().append("g").attr("class", "arc");

    arcs.append("path")
        // @ts-ignore
        .attr("d", arc)
        // @ts-ignore
        .attr("fill", (d) => color(dataKey(d)));

    // Create Legend
    svg.append("g")
        .attr("transform", `translate(${width / 4},-${height / 2.5})`)
        .call((container) => createLegend(container, color, props.data));

    addTooltips(svg);
}

function createLegend(
    container: d3.Selection<any, any, any, any>,
    color: d3.ScaleOrdinal<string, string>,
    data: DataValuePoint[]
) {
    const titlePadding = 14; // padding between title and entries
    const entrySpacing = 18; // spacing between legend entries
    const entryRadius = 5; // radius of legend entry marks
    const labelOffset = 4; // additional horizontal offset of text labels
    const baselineOffset = 4; // text baseline offset, depends on radius and font size

    container
        .append("text")
        .attr("x", 0)
        .attr("y", 0)
        .attr("fill", "black")
        .attr("font-weight", "bold")
        .attr("font-size", "16px")
        .text(props.title);

    const entries = container
        .selectAll("g")
        .data(data)
        .join("g")
        .attr("transform", (d) => `translate(0, ${titlePadding + d.index * entrySpacing})`);

    entries
        .append("circle")
        .attr("cx", entryRadius) // offset symbol x-position by radius
        .attr("r", entryRadius)
        .attr("fill", (d) => color(dataKey(d)));

    entries
        .append("text")
        .attr("x", 2 * entryRadius + labelOffset) // place labels to the left of symbols
        .attr("y", baselineOffset) // adjust label y-position for proper alignment
        .attr("fill", "black")
        .attr("font-size", "14px")
        .text((d) => props.tooltipFormatter(d));
}

function addTooltips(svg: d3.Selection<SVGGElement, unknown, null, undefined>) {
    const tooltip = d3.select(chart.value).append("div").attr("class", "tooltip").style("opacity", 0);

    svg.selectAll("path")
        .on("mouseover", (event, d) => {
            tooltip.transition().duration(200).style("opacity", 1.0);
            tooltip
                // @ts-ignore
                .html(props.tooltipFormatter(d.data))
                .style("font-size", "18px")
                .style("left", `${event.pageX}px`)
                .style("top", `${event.pageY - 28}px`);
        })
        .on("mouseout", () => {
            tooltip.transition().duration(500).style("opacity", 0);
        });
}

function dataKey(d: DataValuePoint): string {
    return `${d.index}`;
}
</script>

<template>
    <div ref="chart" class="pieChart"></div>
</template>

<style lang="css" scoped>
.pieChart {
    text-align: center;
}

.tooltip {
    position: absolute;
    background-color: white;
    border: 1px solid #ddd;
    padding: 10px;
}
</style>
