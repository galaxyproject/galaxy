<script setup lang="ts">
import ec2 from "./ec2.json";
import { useJobMetricsStore } from "@/stores/jobMetricsStore";
import { computed, onMounted } from "vue";

const props = defineProps({
    jobId: {
        type: String,
        default: "",
    },
    datasetId: {
        type: String,
        default: "",
    },
    shouldShowAwsEstimate: {
        type: Boolean,
        default: false,
    },
    datasetType: {
        type: String,
        default: "hda",
    },
    includeTitle: {
        type: Boolean,
        default: true,
    },
});

const jobMetricsStore = useJobMetricsStore();

onMounted(async () => {
    if (props.jobId) {
        await jobMetricsStore.fetchJobMetricsForJobId(props.jobId);
    } else {
        await jobMetricsStore.fetchJobMetricsForDatasetId(props.datasetId, props.datasetType);
    }
});

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

        const group = pluginGroups[metric.plugin];
        group[metric.title] = metric.value;
    }

    return pluginGroups;
});

const pluginsSortedByPluginType = computed(() => {
    return Object.keys(jobMetricsGroupedByPluginType.value).sort();
});

const computedAwsEstimate = computed(() => {
    if (!props.shouldShowAwsEstimate) {
        return;
    }

    const aws: Record<string, any> = {};

    for (const metric of jobMetrics.value) {
        switch (metric.name) {
            case "galaxy_memory_mb":
                aws.memory = parseInt(metric.raw_value);
                break;
            case "galaxy_slots":
                aws.vcpus = parseInt(metric.raw_value);
                break;
            case "runtime_seconds":
                aws.seconds = parseInt(metric.raw_value);
                break;
            default:
        }
    }

    if (aws.memory) {
        aws.memory /= 1024;
    } else {
        // if memory was not specified, assign the smallest amount (we judge based on CPU-count only)
        aws.memory = 0.5;
    }

    // ec2 is already pre-sorted
    aws.instance = ec2.find((ec) => {
        return ec.mem >= aws.memory && ec.vcpus >= aws.vcpus;
    });

    if (!aws.instance) {
        return;
    }

    aws.price = ((aws.seconds * aws.instance.price) / 3600).toFixed(2);

    return aws;
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

        <div v-if="shouldShowAwsEstimate && computedAwsEstimate" id="aws-estimate">
            <div class="aws">
                <h3>AWS estimate</h3>

                <b>{{ computedAwsEstimate.price }} USD</b><br />
                This job requested {{ computedAwsEstimate.vcpus }} core{{
                    computedAwsEstimate.vcpus > 1 ? "s" : ""
                }}
                and {{ computedAwsEstimate.memory }} Gb. Given this information, the smallest EC2 machine we could find
                is <span id="aws_name">{{ computedAwsEstimate.instance.name }}</span> (<span id="aws_mem">{{
                    computedAwsEstimate.instance.mem
                }}</span>
                GB / <span id="aws_vcpus">{{ computedAwsEstimate.instance.vcpus }}</span> vCPUs /
                <span id="aws_cpu">{{ computedAwsEstimate.instance.cpu }}</span
                >). This instance is priced at {{ computedAwsEstimate.instance.price }} USD/hour.<br />
                &ast;Please note, that these numbers are only estimates, all jobs are always free of charge for all
                users.
            </div>
        </div>
    </div>
</template>

<style scoped>
.aws {
    padding-top: 0.6rem;
}
</style>
