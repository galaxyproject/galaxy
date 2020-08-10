<template>
    <div>
        <div v-if="!isSingleParam" class="tool-parameters">
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
                            <JobParametersArrayValue :parameter_value="parameter.value" />
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
        <div id="single-param" v-if="isSingleParam">
            <div v-if="Array.isArray(singleParam)">
                <JobParametersArrayValue :parameter_value="singleParam" />
            </div>
            <td v-else>
                {{ singleParam }}
            </td>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import JobParametersArrayValue from "./JobParametersArrayValue";

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
        param: {
            type: String,
        },
        includeTitle: {
            type: Boolean,
            default: true,
        },
    },
    components: {
        JobParametersArrayValue,
    },
    data() {
        return {
            parameters: [],
            hasParameterErrors: false,
            isSingleParam: false,
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
        this.isSingleParam = this.param !== undefined && this.param !== "undefined";
    },
    computed: {
        anyNotes: function () {
            let hasNotes = false;
            this.parameters.forEach((parameter) => {
                hasNotes = hasNotes || parameter.notes;
            });
            return hasNotes;
        },
        singleParam: function () {
            if (!this.isSingleParam) return;
            const parameter = this.parameters.find((parameter) => {
                return parameter.text === this.param;
            });
            return parameter ? parameter.value : `Parameter "${this.param}" is not found!`;
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
