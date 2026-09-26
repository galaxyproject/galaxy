<template>
    <div>
        <div v-if="!isSingleParam" class="tool-parameters">
            <Heading v-if="includeTitle" id="tool-parameters-heading" h1 separator inline size="md">
                Tool Parameters
            </Heading>
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
                        <td v-else-if="isRequestJson(parameter)" class="tool-parameter-value">
                            <DataFetchRequestParameter :parameter-value="parameter.value" />
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
        <template v-if="includeOutputs">
            <br />
            <JobOutputs :job-outputs="outputs" paginate :title="`Job Outputs`" />
        </template>
    </div>
</template>

<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useJobParametersStore } from "@/stores/jobParametersStore";

import Heading from "../Common/Heading.vue";
import JobOutputs from "../JobInformation/JobOutputs.vue";
import DataFetchRequestParameter from "./DataFetchRequestParameter.vue";
import JobParametersArrayValue from "./JobParametersArrayValue.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        DataFetchRequestParameter,
        Heading,
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
        /** Append the JobOutputs table at the bottom (set false when callers
         *  already render outputs in a separate UI surface). */
        includeOutputs: {
            type: Boolean,
            default: true,
        },
    },
    setup() {
        return { jobParametersStore: useJobParametersStore() };
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
    watch: {
        jobId: function (newValue) {
            this.initJob();
        },
    },
    created: function () {
        this.initJob();
    },
    methods: {
        isRequestJson(parameter) {
            return parameter.text == "request_json" && typeof parameter.value == "string";
        },
        async initJob() {
            this.isSingleParam = this.param !== undefined && this.param !== "undefined";
            if (this.jobId) {
                try {
                    await this.jobParametersStore.fetchJobParameters({ id: this.jobId });
                    const data = this.jobParametersStore.getJobParameters(this.jobId);
                    if (data) {
                        this.applyData(data);
                    }
                } catch (e) {
                    console.error(e);
                }
            } else if (this.datasetId) {
                const url = `${getAppRoot()}api/datasets/${this.datasetId}/parameters_display?hda_ldda=${this.datasetType}`;
                this.ajaxCall(url);
            }
        },
        appRoot: function () {
            return getAppRoot();
        },
        ajaxCall: function (url) {
            axios
                .get(url)
                .then((response) => response.data)
                .then((data) => this.applyData(data))
                .catch((e) => {
                    console.error(e);
                });
        },
        applyData(data) {
            this.hasParameterErrors = data.has_parameter_errors;
            this.parameters = data.parameters;
            this.outputs = data.outputs || {};
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
