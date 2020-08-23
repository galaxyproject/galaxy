<template>
    <div v-if="invocation">
        <div v-if="Object.keys(invocation.input_step_parameters).length > 0">
            <details
                ><summary><b>Invocation Parameters</b></summary>
                <b-table small caption-top :fields="['label', 'parameter_value']" :items="Object.values(invocation.input_step_parameters)"/>
            </details>
        </div>
        <div v-if="Object.keys(invocation.inputs).length > 0">
            <details
                ><summary><b>Invocation Inputs</b></summary>
                <div v-for="input in invocation.inputs" v-bind:key="input.id">
                    <WorkflowInvocationOutputs v-bind:data_item="input" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.outputs).length > 0">
            <details
                ><summary><b>Invocation Outputs</b></summary>
                <div v-for="output in invocation.outputs" v-bind:key="output.id">
                    <WorkflowInvocationOutputs v-bind:data_item="output" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.output_collections).length > 0">
            <details
                ><summary><b>Invocation Output Collections</b></summary>
                <div v-for="output in invocation.output_collections" v-bind:key="output.id">
                    <WorkflowInvocationOutputs v-bind:data_item="output" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.steps).length > 0">
            <details
                ><summary><b>Invocation Steps</b></summary>
                <div v-for="step in invocation.steps" v-bind:key="step.id">
                    {{ step }}
                </div>
            </details>
        </div>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { Dataset } from "components/History/ContentItem/Dataset";
import WorkflowInvocationOutputs from "./WorkflowInvocationOutputs";
import ListMixin from "components/History/ListMixin";

import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

import { getRootFromIndexLink } from "onload";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

Vue.use(BootstrapVue);

export default {
    mixins: [ListMixin],
    components: {
        WorkflowInvocationOutputs,
    },
    props: {
        invocation: {
            required: true,
        },
    },
};
</script>
