<template>
    <div v-if="orderedPlugins.length > 0">
        <h3 v-if="includeTitle">Job Metrics</h3>
        <div v-for="plugin in orderedPlugins" v-bind:key="plugin" class="metrics_plugin">
            <h4 class="metrics_plugin_title">{{ plugin }}</h4>
            <table class="tabletip info_data_table">
                <tbody>
                    <tr v-for="(metricValue, metricTitle) in metricsByPlugins[plugin]" v-bind:key="metricTitle">
                        <td>{{ metricTitle }}</td>
                        <td>{{ metricValue }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";

export default {
    props: {
        jobId: {
            type: String
        },
        datasetId: {
            type: String
        },
        datasetType: {
            type: String,
            default: "hda"
        },
        includeTitle: {
            type: Boolean,
            default: true
        }
    },
    data() {
        return {};
    },
    created: function() {
        if (this.jobId) {
            this.fetchJobMetricsForJobId(this.jobId);
        } else {
            this.fetchJobMetricsForDatasetId({ datasetId: this.datasetId, datasetType: this.datasetType });
        }
    },
    computed: {
        ...mapGetters(["getJobMetricsByDatasetId", "getJobMetricsByJobId"]),
        jobMetrics: function() {
            if (this.jobId) {
                return this.getJobMetricsByJobId(this.jobId);
            } else {
                return this.getJobMetricsByDatasetId(this.datasetId, this.datasetType);
            }
        },
        metricsByPlugins: function() {
            const metricsByPlugins = {};
            const metrics = this.jobMetrics;
            metrics.forEach(metric => {
                if (!(metric.plugin in metricsByPlugins)) {
                    metricsByPlugins[metric.plugin] = {};
                }
                const metricsForPlugin = metricsByPlugins[metric.plugin];
                metricsForPlugin[metric.title] = metric.value;
            });
            return metricsByPlugins;
        },
        orderedPlugins: function() {
            return Object.keys(this.metricsByPlugins).sort();
        }
    },
    methods: {
        ...mapCacheActions(["fetchJobMetricsForDatasetId", "fetchJobMetricsForJobId"])
    }
};
</script>
