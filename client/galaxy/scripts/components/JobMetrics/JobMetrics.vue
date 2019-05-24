<template>
    <div v-if="metricsByPlugins">
        <h3 v-if="includeTitle">Job Metrics</h3>
        <div v-for="plugin in orderedPlugins" v-bind:key="plugin">
            <h4>{{ plugin }}</h4>
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
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

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
        return {
            metricsByPlugins: {}
        };
    },
    created: function() {
        let url;
        if (this.jobId) {
            url = `${getAppRoot()}api/jobs/${this.jobId}/metrics`;
        } else {
            url = `${getAppRoot()}api/datasets/${this.datasetId}/metrics?hda_ldda=${this.datasetType}`;
        }
        this.ajaxCall(url);
    },
    computed: {
        orderedPlugins: function() {
            return Object.keys(this.metricsByPlugins).sort();
        }
    },
    methods: {
        ajaxCall: function(url) {
            axios
                .get(url)
                .then(response => {
                    const metricsByPlugins = {};
                    const metrics = response.data;
                    metrics.forEach(metric => {
                        if (!(metric.plugin in metricsByPlugins)) {
                            metricsByPlugins[metric.plugin] = {};
                        }
                        const metricsForPlugin = metricsByPlugins[metric.plugin];
                        metricsForPlugin[metric.title] = metric.value;
                    });
                    this.metricsByPlugins = metricsByPlugins;
                })
                .catch(e => {
                    console.error(e);
                });
        }
    }
};
</script>
