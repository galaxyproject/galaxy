<template>
    <div>
        <div v-if="!isSingleParam" class="tool-parameters">
            <h3 v-if="includeTitle">Tool Parameters</h3>
            <table id="tool-parameters" class="tabletip info_data_table">
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
                        <td v-else class="tool-parameter-value">
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
        <div v-if="isSingleParam" id="single-param">
            <div v-if="Array.isArray(singleParam)">
                <JobParametersArrayValue :parameter_value="singleParam" />
            </div>
            <td v-else>
                {{ singleParam }}
            </td>
        </div>
        <br />
        <job-outputs :job-outputs="outputs" :title="`Job Outputs`" />
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import JobOutputs from "../JobInformation/JobOutputs";
import JobParametersArrayValue from "./JobParametersArrayValue";

Vue.use(BootstrapVue);

export default {
    components: {
        JobOutputs,
        JobParametersArrayValue,
    },
    props: {
        jobId: {
            type: String,
            default: null,
        },
        datasetId: {
            type: String,
            default: null,
        },
        datasetType: {
            type: String,
            default: "hda",
        },
        param: {
            type: String,
            default: undefined,
        },
        includeTitle: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {
            parameters: [],
            outputs: {},
            hasParameterErrors: false,
            isSingleParam: false,
        };
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
            if (!this.isSingleParam) {
                return;
            }
            const parameter = this.parameters.find((parameter) => {
                return parameter.text === this.param;
            });
            return parameter ? parameter.value : `Parameter "${this.param}" is not found!`;
        },
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
                    this.outputs = data.outputs;
                })
                .catch((e) => {
                    console.error(e);
                });
        },
    },
};
</script>

<style scoped>
.tool-parameter-value {
    overflow: auto;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 20;
    -webkit-box-orient: vertical;
}
</style>
