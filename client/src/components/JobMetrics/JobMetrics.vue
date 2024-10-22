<script setup lang="ts">
import { computed, ref, unref, watch } from "vue";

import { useJobMetricsStore } from "@/stores/jobMetricsStore";

import { worldwideCarbonIntensity, worldwidePowerUsageEffectiveness } from "./CarbonEmissions/carbonEmissionConstants";

import AwsEstimate from "./AwsEstimate.vue";
import CarbonEmissions from "./CarbonEmissions/CarbonEmissions.vue";

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
    powerUsageEffectiveness: {
        type: Number,
        default: worldwidePowerUsageEffectiveness,
    },
    geographicalServerLocationName: {
        type: String,
        default: "GLOBAL",
    },
    carbonIntensity: {
        type: Number,
        default: worldwideCarbonIntensity,
    },
    shouldShowAwsEstimate: {
        type: Boolean,
        default: false,
    },
    shouldShowCarbonEmissionEstimates: {
        type: Boolean,
        default: true,
    },
});

const jobMetricsStore = useJobMetricsStore();

async function getJobMetrics() {
    if (props.jobId) {
        await jobMetricsStore.fetchJobMetricsForJobId(props.jobId);
    } else {
        await jobMetricsStore.fetchJobMetricsForDatasetId(props.datasetId, props.datasetType);
    }
}

watch(
    props,
    () => {
        getJobMetrics();
    },
    { immediate: true }
);

const ec2Instances = ref<EC2[]>();
import("./awsEc2ReferenceData.js").then((data) => (ec2Instances.value = data.ec2Instances));

type EC2 = {
    name: string;
    mem: number;
    price: number;
    priceUnit: string;
    vCpuCount: number;
    cpu: {
        cpuModel: string;
        tdp: number;
        coreCount: number;
        source: string;
    }[];
};

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

function getMetricByName(key: string) {
    return jobMetrics.value.find(({ name }) => name === key)?.raw_value;
}

const jobRuntimeInSeconds = computed(() => {
    const runtime = getMetricByName("runtime_seconds");

    return runtime ? parseInt(runtime) : undefined;
});

const coresAllocated = computed(() => {
    const coreCount = getMetricByName("galaxy_slots");

    return coreCount ? parseInt(coreCount) : undefined;
});

const memoryAllocatedInMebibyte = computed(() => {
    const memoryUsage = getMetricByName("galaxy_memory_mb");

    return memoryUsage ? parseInt(memoryUsage) : undefined;
});

const estimatedServerInstance = computed(() => {
    const cores = unref(coresAllocated);
    if (!cores) {
        return;
    }

    const memory = unref(memoryAllocatedInMebibyte);
    const adjustedMemory = memory ? memory / 1024 : 0;

    const ec2 = unref(ec2Instances);
    if (!ec2) {
        return;
    }

    const serverInstance = ec2.find((instance) => {
        if (adjustedMemory === 0) {
            // Exclude memory from search criteria
            return instance.vCpuCount >= cores;
        }

        // Search by all criteria
        return instance.mem >= adjustedMemory && instance.vCpuCount >= cores;
    });

    if (!serverInstance) {
        return;
    }

    const cpu = serverInstance.cpu[0];
    if (!cpu) {
        return;
    }

    return {
        name: serverInstance.name,
        cpuInfo: {
            modelName: cpu.cpuModel,
            totalAvailableCores: cpu.coreCount,
            tdp: cpu.tdp,
        },
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
            v-if="jobRuntimeInSeconds && coresAllocated && ec2Instances && shouldShowAwsEstimate"
            :ec2-instances="ec2Instances"
            :job-runtime-in-seconds="jobRuntimeInSeconds"
            :cores-allocated="coresAllocated"
            :memory-allocated-in-mebibyte="memoryAllocatedInMebibyte" />

        <CarbonEmissions
            v-if="shouldShowCarbonEmissionEstimates && estimatedServerInstance && jobRuntimeInSeconds && coresAllocated"
            :carbon-intensity="carbonIntensity"
            :geographical-server-location-name="geographicalServerLocationName"
            :power-usage-effectiveness="powerUsageEffectiveness"
            :estimated-server-instance="estimatedServerInstance"
            :job-runtime-in-seconds="jobRuntimeInSeconds"
            :cores-allocated="coresAllocated"
            :memory-allocated-in-mebibyte="memoryAllocatedInMebibyte" />
    </div>
</template>
