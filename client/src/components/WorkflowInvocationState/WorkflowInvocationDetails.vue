<template>
    <div v-if="invocation" class="mb-3">
        <div v-if="Object.keys(invocation.input_step_parameters).length > 0">
            <details><summary><b>Invocation Parameters</b></summary>
                <div v-for="parameter in invocation.input_step_parameters" v-bind:key="parameter.id">
                    {{parameter}}
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.outputs).length > 0">
            <details><summary><b>Invocation Outputs</b></summary>
                <div v-for="output in invocation.outputs" v-bind:key="output.id">
                    {{output}}
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.output_collections).length > 0">
            <details><summary><b>Invocation Output Collections</b></summary>
                <div v-for="output in invocation.output_collections" v-bind:key="output.id">
                    {{output}}
                </div>
            </details>
        </div>
        <div>
            <details><summary><b>Invocation Steps</b></summary>
                <div v-for="step in invocation.steps" v-bind:key="step.id">
                    {{step}}
                </div>
            </details>
        </div>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { getRootFromIndexLink } from "onload";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

Vue.use(BootstrapVue);

export default {
    props: {
        invocation: {
            required: true,
        }
    }
}
</script>