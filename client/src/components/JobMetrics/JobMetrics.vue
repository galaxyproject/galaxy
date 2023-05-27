<script setup lang="ts">
import AwsEstimate from "./AwsEstimate.vue";
import CarbonEmissions from "@/components/CarbonEmissions/CarbonEmissions.vue";
import ec2 from "./ec2.json";
import { useJobMetricsStore } from "@/stores/jobMetricsStore";
import { computed, unref } from "vue";

export interface JobMetricsProps {
    datasetFilesize?: number;
    datasetId?: string;
    datasetType?: string;
    includeTitle?: boolean;
    jobId: string;
    shouldShowAwsEstimate?: boolean;
}

const props = withDefaults(defineProps<JobMetricsProps>(), {
    datasetFilesize: 0,
    datasetId: "",
    datasetType: "hda",
    includeTitle: true,
    shouldShowAwsEstimate: false
});

const jobMetricsStore = useJobMetricsStore();

async function getJobMetrics() {
    if (props.jobId) {
        await jobMetricsStore.fetchJobMetricsForJobId(props.jobId);
    } else {
        await jobMetricsStore.fetchJobMetricsForDatasetId(props.datasetId, props.datasetType);
    }
}
getJobMetrics();

function getMetricByName(key: string) {
    return jobMetrics.value.find(({ name }) => name === key)?.raw_value;
}

const jobMetrics = computed(() => {
    if (props.jobId) {
        return jobMetricsStore.getJobMetricsByJobId(props.jobId);
    } else {
        return jobMetricsStore.getJobMetricsByDatasetId(props.datasetId, props.datasetType);
    }
});

const jobMetricsGroupedByPluginType = computed(() => {
    const pluginGroups: Record<string, any> = {};

    for (const metric of jobMetrics.value) {
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

const pluginsSortedByPluginType = computed(() => {
    return Object.keys(jobMetricsGroupedByPluginType.value).sort();
});

const jobRuntime = computed(() => {
    const runtime = getMetricByName("runtime_seconds");

    return runtime ? parseInt(runtime) : undefined;
});

const coresAllocated = computed(() => {
    const coreCount = getMetricByName("galaxy_slots");

    return coreCount ? parseInt(coreCount) : undefined;
});

const memoryAllocated = computed(() => {
    const memoryUsage = getMetricByName("galaxy_memory_mb");

    return memoryUsage ? parseInt(memoryUsage) : undefined;
});

const estimatedServerInstance = computed(() => {
    const cores = unref(coresAllocated);
    if (!cores) {
        return;
    }

    let serverInstance: (typeof ec2)[number] | undefined;

    const memory = unref(memoryAllocated);
    const adjustedMemory = memory ? memory / 1024 : 0;

    if (adjustedMemory === 0) {
        serverInstance = ec2.find((ec) => ec.vcpus >= cores);
    } else {
        serverInstance = ec2.find((ec) => ec.mem >= adjustedMemory && ec.vcpus >= cores);
    }

    if (!serverInstance) {
        return;
    }

    return {
        name: serverInstance.name,
        cpuModel: serverInstance.cpu,
        coreCount: serverInstance.vcpus,
        memory: serverInstance.mem,
    };
});
</script>

<template>
    <div v-if="pluginsSortedByPluginType.length > 0">
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
            v-if="jobRuntime && coresAllocated"
            :should-show-aws-estimate="shouldShowAwsEstimate"
            :job-runtime="jobRuntime"
            :cores-allocated="coresAllocated"
            :memory-allocated="memoryAllocated" />

        <CarbonEmissions
            v-if="estimatedServerInstance && jobRuntime && coresAllocated"
            :estimated-server-instance="estimatedServerInstance"
            :job-runtime="jobRuntime"
            :cores-allocated="coresAllocated"
            :memory-allocated="memoryAllocated" />
    </div>
</template>
