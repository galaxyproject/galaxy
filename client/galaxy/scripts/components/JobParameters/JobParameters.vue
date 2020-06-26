<template>
    <div class="tool-parameters">
        <h3 v-if="includeTitle">Tool Parameters</h3>
        <table class="tabletip" id="tool-parameters">
            <thead>
                <tr>
                    <th>Input Parameter</th>
                    <th>Value</th>
                    <th v-if="anyNotes">Note for rerun</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(parameter, pIndex) in parameters" :key="pIndex">
                    <td :style="{ 'padding-left': `${(parameter.depth - 1) * 10}px` }">
                        {{ parameter.text }}
                    </td>
                    <td v-if="Array.isArray(parameter.value)">
                        <ul style="padding-inline-start: 25px;">
                            <li v-for="(elVal, pvIndex) in parameter.value" :key="pvIndex">
                                <span v-if="elVal.src == 'hda'">
                                    <a :href="appRoot() + 'datasets/' + elVal.id + '/show_params'">
                                        {{ elVal.hid }}: {{ elVal.name }}
                                    </a>
                                </span>
                                <span v-else> {{ elVal.hid }}: {{ elVal.name }} </span>
                            </li>
                        </ul>
                    </td>
                    <td v-else>
                        {{ parameter.value }}
                    </td>
                    <td v-if="anyNotes">
                        <em v-if="parameter.notes">{{ parameter.notes }}</em>
                    </td>
                </tr>
            </tbody>
        </table>
        <b-alert :show="hasParameterErrors" variant="danger">
            One or more of your original parameters may no longer be valid or displayed properly.
        </b-alert>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        jobId: {
            type: String,
        },
        datasetId: {
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
        return {
            parameters: [],
            hasParameterErrors: false,
        };
    },
    created: function () {
        let url;
        if (this.jobId) {
            url = `${getAppRoot()}api/jobs/${this.jobId}/parameters_display`;
        } else {
            url = `${getAppRoot()}api/datasets/${this.datasetId}/parameters_display?hda_ldda=${this.datasetType}`;
        }
        this.ajaxCall(url);
    },
    computed: {
        anyNotes: function () {
            let hasNotes = false;
            this.parameters.forEach((parameter) => {
                hasNotes = hasNotes || parameter.notes;
            });
            return hasNotes;
        },
    },
    methods: {
        appRoot: function () {
            return getAppRoot();
        },
        ajaxCall: function (url) {
            axios
                .get(url)
                .then((response) => response.data)
                .then((data) => {
                    this.hasParameterErrors = data.has_parameter_errors;
                    this.parameters = data.parameters;
                })
                .catch((e) => {
                    console.error(e);
                });
        },
    },
};
</script>
<style scoped>
table.info_data_table {
    table-layout: fixed;
    word-break: break-word;
}
table.info_data_table td:nth-child(1) {
    width: 25%;
}
</style>
