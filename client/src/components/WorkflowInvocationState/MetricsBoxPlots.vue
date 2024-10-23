<template>
  <div ref="boxPlot"></div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import * as d3 from 'd3';
import { isTerminal } from './util';

interface JobData {
  title: string;
  value: string;
  plugin: string;
  name: string;
  raw_value: string;
  tool_id: string;
}


const boxPlot = ref<HTMLElement | null>(null);

// Define the job data (this can come from props or API in real scenario// Extract runtime seconds data
// Define props
const props = defineProps<{
  jobData: JobData[];
}>();

// Function to render box plots for different tool_ids on the same graph
const renderBoxPlots = () => {
  const margin = { top: 10, right: 30, bottom: 50, left: 40 },
    width = 800 - margin.left - margin.right,
    height = 400 - margin.top - margin.bottom;

  // Remove any previous content
  d3.select(boxPlot.value).selectAll('*').remove();

  // Group data by tool_id
  const groupedData = d3.group(props.jobData, d => d.tool_id);

  // Extract the tool_ids for the x-axis
  const toolIds = Array.from(groupedData.keys());

  // Create SVG
  const svg = d3
    .select(boxPlot.value)
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  // X Scale: tool_ids on the x-axis
  const x = d3.scaleBand()
    .range([0, width])
    .domain(toolIds)
    .padding(0.4);

  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x));

  // Y Scale: common for all box plots
  const allRuntimes = Array.from(props.jobData)
    .filter(d => d.name === "runtime_seconds")
    .map(d => parseFloat(d.raw_value));

  const y = d3.scaleLinear()
    .domain([0, d3.max(allRuntimes) as number])
    .range([height, 0]);

  svg.append('g').call(d3.axisLeft(y));

  // Tooltip for individual dots
  const tooltip = d3.select(boxPlot.value)
    .append("div")
    .style("position", "absolute")
    .style("background", "lightgray")
    .style("padding", "5px")
    .style("border-radius", "5px")
    .style("pointer-events", "none")
    .style("visibility", "hidden");

  // Render box plots for each tool_id
  groupedData.forEach((data, toolId) => {
    const runtimeData = data.map(d => parseFloat(d.raw_value));

    const center = x(toolId) as number + x.bandwidth() / 2;
    const boxWidth = x.bandwidth() / 2;

    const q1 = d3.quantile(runtimeData.sort(d3.ascending), 0.25) as number;
    const median = d3.quantile(runtimeData.sort(d3.ascending), 0.5) as number;
    const q3 = d3.quantile(runtimeData.sort(d3.ascending), 0.75) as number;
    const interQuantileRange = q3 - q1;
    const min = Math.max(d3.min(runtimeData) as number, q1 - 1.5 * interQuantileRange);
    const max = Math.min(d3.max(runtimeData) as number, q3 + 1.5 * interQuantileRange);

    // Box
    svg.append('rect')
      .attr('x', center - boxWidth / 2)
      .attr('y', y(q3))
      .attr('height', y(q1) - y(q3))
      .attr('width', boxWidth)
      .attr('stroke', 'black')
      .style('fill', '#69b3a2');

    // Median, min, max lines
    svg.selectAll('line')
      .data([min, median, max])
      .enter()
      .append('line')
      .attr('x1', center - boxWidth / 2)
      .attr('x2', center + boxWidth / 2)
      .attr('y1', d => y(d))
      .attr('y2', d => y(d))
      .attr('stroke', 'black');

    // Vertical lines for min-max
    svg.append('line')
      .attr('x1', center)
      .attr('x2', center)
      .attr('y1', y(min))
      .attr('y2', y(q1))
      .attr('stroke', 'black');

    svg.append('line')
      .attr('x1', center)
      .attr('x2', center)
      .attr('y1', y(max))
      .attr('y2', y(q3))
      .attr('stroke', 'black');

    // Add individual data points (dots)
    svg.selectAll("circle")
      .data(runtimeData)
      .enter()
      .append("circle")
      .attr("cx", center) // Align horizontally to the center of the group
      .attr("cy", d => y(d)) // Map the data value to the y-axis
      .attr("r", 5) // Radius of the circle
      .style("fill", "#ff5722") // Fill color for the points
      .attr("stroke", "black")
      .on("mouseover", function (event, d) {
        tooltip.style("visibility", "visible")
          .text(`Value: ${d}`);
        d3.select(this).style("fill", "yellow");
      })
      .on("mousemove", function (event) {
        tooltip.style("top", `${event.pageY - 10}px`)
          .style("left", `${event.pageX + 10}px`);
      })
      .on("mouseout", function () {
        tooltip.style("visibility", "hidden");
        d3.select(this).style("fill", "#ff5722");
      });
  });
};

// Lifecycle hook to render the plot once the component is mounted
onMounted(() => {
  renderBoxPlots();
});

</script>

<style scoped>
svg {
  font-family: Arial, sans-serif;
}
</style>
