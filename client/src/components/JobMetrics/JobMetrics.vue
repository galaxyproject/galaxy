<script setup lang="ts">
import { computed, onMounted, unref, watch } from "vue";

import { useConfig } from "@/composables/config";
import { useJobMetricsStore } from "@/stores/jobMetricsStore";

import AwsEstimate from "./AwsEstimate.vue";
import JobCarbonEmissions from "./JobCarbonEmissions.vue";

const props = defineProps({
    datasetFilesize: {
        type: Number,
        default: 0,
    },
    datasetId: {
        type: String,
        default: "",
    },
    datasetType: {
        type: String,
        default: "hda",
    },
    includeTitle: {
        type: Boolean,
        default: true,
    },
    jobId: {
        type: String,
        default: null,
    },
});

const jobMetricsStore = useJobMetricsStore();

const { config } = useConfig(true);
const shouldShowAwsEstimate = (config.value.aws_estimate as boolean) ?? false;
const shouldShowCarbonEmissionsEstimates = (config.value.carbon_emissions_estimates as boolean) ?? true;

const jobMetrics = computed(() => {
    if (props.jobId) {
        return jobMetricsStore.getJobMetricsByJobId(props.jobId);
    }
    return jobMetricsStore.getJobMetricsByDatasetId(props.datasetId, props.datasetType);
});

const jobMetricsGroupedByPluginType = computed(() => {
    const pluginGroups: Record<string, any> = {};
    const ignoredMetrics = [
        "energy_needed_cpu",
        "energy_needed_memory",
        "estimated_server_instance_name",
    ];

    for (const metric of jobMetrics.value) {
        if (ignoredMetrics.includes(metric.name)) {
          continue;
        }

        // new group found
        if (!(metric.plugin in pluginGroups)) {
            pluginGroups[metric.plugin] = {};
        }

        // Add metric to group
        const group = pluginGroups[metric.plugin];
        group[metric.title] = metric.value;
    }

    return pluginGroups;
});

const energyUsage = computed(() => {
    const energyNeededCPU = jobMetrics.value.find(({ name }) => name === "energy_needed_cpu")?.raw_value;
    if (!energyNeededCPU) {
        return;
    }

    const energyNeededMemory = jobMetrics.value.find(({ name }) => name === "energy_needed_memory")?.raw_value;
    if (!energyNeededMemory) {
        return {
            energyNeededCPU: parseFloat(energyNeededCPU),
            energyNeededMemory: 0.0,
        };
    }

    return {
        energyNeededCPU: parseFloat(energyNeededCPU),
        energyNeededMemory: parseFloat(energyNeededMemory),
    };
});

const pluginsSortedByPluginType = computed(() => {
    return Object.keys(jobMetricsGroupedByPluginType.value).sort();
});

const hasPluginsToDisplay = computed(() => {
    return pluginsSortedByPluginType.value.length > 0;
});

const jobRuntimeInSeconds = computed(() => {
    const key = "runtime_seconds";
    const runtime = unref(jobMetrics).find(({ name }) => name === key)?.raw_value;

    return runtime ? parseInt(runtime) : undefined;
});

const coresAllocated = computed(() => {
    const key = "galaxy_slots";
    const coreCount = unref(jobMetrics).find(({ name }) => name === key)?.raw_value;

    return coreCount ? parseInt(coreCount) : undefined;
});

const memoryAllocatedInMebibyte = computed(() => {
    const key = "galaxy_memory_mb";
    const memoryUsage = unref(jobMetrics).find(({ name }) => name === key)?.raw_value;

    return memoryUsage ? parseInt(memoryUsage) : undefined;
});

const estimatedServerInstanceName = computed(() => {
    const key = "estimated_server_instance_name";
    const name = unref(jobMetrics).find(({ name }) => name === key)?.raw_value;

    return name ? name : undefined;
});

async function fetchJobMetrics() {
    if (props.jobId) {
        await jobMetricsStore.fetchJobMetricsForJobId(props.jobId);
    }
    await jobMetricsStore.fetchJobMetricsForDatasetId(props.datasetId, props.datasetType);
}

onMounted(() => {
    fetchJobMetrics();
});

watch(
    props,
    () => {
        fetchJobMetrics();
    },
    {
        immediate: true,
    }
);
</script>

<template>
    <div v-if="hasPluginsToDisplay">
        <h2 v-if="includeTitle" class="h-md">Job Metrics</h2>

        <div v-for="pluginType in pluginsSortedByPluginType" :key="pluginType" class="metrics_plugin">
            <h3 class="metrics_plugin_title m-sm">{{ pluginType }}</h3>

            <table class="tabletip info_data_table">
                <tbody>
                    <tr
                        v-for="(metricValue, metricTitle) in jobMetricsGroupedByPluginType[pluginType]"
                        :key="metricTitle">
                        <td>{{ metricTitle }}</td>
                        <td>{{ metricValue }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <AwsEstimate
            v-if="shouldShowAwsEstimate && jobRuntimeInSeconds && coresAllocated"
            :job-runtime-in-seconds="jobRuntimeInSeconds"
            :cores-allocated="coresAllocated"
            :memory-allocated-in-mebibyte="memoryAllocatedInMebibyte" />

        <JobCarbonEmissions
            v-if="shouldShowCarbonEmissionsEstimates && energyUsage && estimatedServerInstanceName"
            :energy-usage="energyUsage"
            :estimated-server-instance-name="estimatedServerInstanceName" />
    </div>
</template>
