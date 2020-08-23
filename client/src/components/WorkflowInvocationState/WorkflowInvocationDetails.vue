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
                <div v-for="(input, key) in invocation.inputs" v-bind:key="input.id">
                    <b>{{dataInputStepLabel(key, input)}}</b>
                    <workflow-invocation-data-contents v-bind:data_item="input" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.outputs).length > 0">
            <details
                ><summary><b>Invocation Outputs</b></summary>
                <div v-for="(output, key) in invocation.outputs" v-bind:key="output.id">
                    <b>{{key}}:</b> <workflow-invocation-data-contents v-bind:data_item="output" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.output_collections).length > 0">
            <details
                ><summary><b>Invocation Output Collections</b></summary>
                <div v-for="(output, key) in invocation.output_collections" v-bind:key="output.id">
                    <b>{{key}}:</b> <workflow-invocation-data-contents v-bind:data_item="output" />
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
import WorkflowInvocationDataContents from "./WorkflowInvocationDataContents";
import ListMixin from "components/History/ListMixin";

import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import _ from 'lodash';

import { getRootFromIndexLink } from "onload";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

Vue.use(BootstrapVue);

export default {
    mixins: [ListMixin],
    components: {
        WorkflowInvocationDataContents,
    },
    props: {
        invocation: {
            required: true,
        },
    },
    computed: {
        orderedSteps() {
            return _.orderBy(this.invocation.steps, ['order_index']);
        }
    },
    methods: {
        dataInputStepLabel(key, input) {
            let label = this.orderedSteps[key].workflow_step_label;
            if (!label) {
                if (input.src === 'hda' || input.src === 'ldda') {
                    label = 'Input dataset'
                } else if (input.src === 'hdca') {
                    label = 'Input dataset collection'
                }
            }
            return label
        }
    },
};
</script>
