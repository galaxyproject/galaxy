<template>
    <div v-if="orderedPlugins.length > 0">
        <h3 v-if="includeTitle">Job Metrics</h3>
        <div v-for="plugin in orderedPlugins" :key="plugin" class="metrics_plugin">
            <h4 class="metrics_plugin_title">{{ plugin }}</h4>
            <table class="tabletip info_data_table">
                <tbody>
                    <tr v-for="(metricValue, metricTitle) in metricsByPlugins[plugin]" :key="metricTitle">
                        <td>{{ metricTitle }}</td>
                        <td>{{ metricValue }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div id="aws-estimate" v-if="isAwsEstimate && awsEstimate">
            <h3>AWS estimate</h3>
            <b>{{ awsEstimate.price }} USD</b><br />
            This job requested {{ awsEstimate.vcpus }} cores and {{ awsEstimate.memory }} Gb. Given this, the smallest
            EC2 machine we could find is <span id="aws_name">{{ awsEstimate.instance.name }}</span> (<span
                id="aws_mem"
                >{{ awsEstimate.instance.mem }}</span
            >
            GB / <span id="aws_vcpus">{{ awsEstimate.instance.vcpus }}</span> vCPUs /
            <span id="aws_cpu">{{ awsEstimate.instance.cpu }}</span
            >). That instance is priced at {{ awsEstimate.instance.price }} USD/hour.<br />
            Please note, that those numbers are only estimates, all jobs are always free of charge for all users.
        </div>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";
import ec2 from "./ec2.json";

export default {
    props: {
        jobId: {
            type: String,
        },
        datasetId: {
            type: String,
        },
        aws_estimate: {
            type: String,
        },
        datasetType: {
            type: String,
            default: "hda",
        },
        includeTitle: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {};
    },
    created: function () {
        if (this.jobId) {
            this.fetchJobMetricsForJobId(this.jobId);
        } else {
            this.fetchJobMetricsForDatasetId({ datasetId: this.datasetId, datasetType: this.datasetType });
        }
    },
    computed: {
        ...mapGetters(["getJobMetricsByDatasetId", "getJobMetricsByJobId"]),
        isAwsEstimate: function () {
            return this.aws_estimate && this.aws_estimate.toUpperCase() === "true".toUpperCase();
        },
        awsEstimate: function () {
            if (!this.isAwsEstimate) return;

            const aws = {};
            this.jobMetrics.forEach((metric) => {
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
            });

            if (aws.memory) aws.memory /= 1024;
            // if memory was not specified, assign the smallest amount (we judge based on CPU-count only)
            else aws.memory = 0.5;

            // ec2 is already pre-sorted
            aws.instance = ec2.find((ec) => {
                return ec.mem >= aws.memory && ec.vcpus >= aws.vcpus;
            });
            if (aws.instance === undefined) return;
            aws.price = ((aws.seconds * aws.instance.price) / 3600).toFixed(2);
            return aws;
        },
        jobMetrics: function () {
            if (this.jobId) {
                return this.getJobMetricsByJobId(this.jobId);
            } else {
                return this.getJobMetricsByDatasetId(this.datasetId, this.datasetType);
            }
        },
        metricsByPlugins: function () {
            const metricsByPlugins = {};
            const metrics = this.jobMetrics;
            metrics.forEach((metric) => {
                if (!(metric.plugin in metricsByPlugins)) {
                    metricsByPlugins[metric.plugin] = {};
                }
                const metricsForPlugin = metricsByPlugins[metric.plugin];
                metricsForPlugin[metric.title] = metric.value;
            });
            return metricsByPlugins;
        },
        orderedPlugins: function () {
            return Object.keys(this.metricsByPlugins).sort();
        },
    },
    methods: {
        ...mapCacheActions(["fetchJobMetricsForDatasetId", "fetchJobMetricsForJobId"]),
    },
};
</script>
