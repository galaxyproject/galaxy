<script setup lang="ts">
import { onMounted } from "vue";
import * as d3 from "d3";

const props = defineProps<{
    data: { name: string; value: number }[];
}>();

onMounted(() => {
    const { data } = props;

    const margin = { top: 30, right: 30, bottom: 30, left: 30 };
    const width = 350;
    const height = 200;

    // Create graph SVG
    const svg = d3
        .select("#graph-container")
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // Add X axis
    const x = d3
        .scaleBand()
        .range([0, width])
        .domain(data.map((d) => d.name))
        .padding(0.2);

    svg.append("g")
        .attr("transform", `translate(0, ${height})`)
        .call(d3.axisBottom(x))
        .selectAll("text")
        .style("font-size", "1rem")
        .style("margin", "0.75rem")
        .style("font-weight", "500")
        .style("text-anchor", "middle");

    // Add Y axis
    const y = d3.scaleLinear().domain([0, 100]).range([height, 0]);

    svg.append("g").call(d3.axisLeft(y)).selectAll("text").style("font-size", "0.75rem");

    // Add bars
    svg.selectAll("bar")
        .data(data)
        .join("rect")
        .attr("x", (d) => String(x(d.name)))
        .attr("y", (d) => y(d.value))
        .attr("width", x.bandwidth())
        .attr("height", (d) => height - y(d.value))
        .attr("fill", "#41B883")
        .on("mouseover", mouseOver)
        .on("mouseout", mouseOut);
});

function mouseOver(this: any) {
    d3.select(this).transition().duration(300).attr("opacity", ".5").attr("fill", "red");
}

function mouseOut(this: any) {
    d3.select(this).transition().duration(300).attr("fill", "#41B883").attr("opacity", "1");
}
</script>

<template>
    <div id="graph-container" />
</template>
