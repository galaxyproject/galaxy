<template>
    <div>
        <tr v-for="(elVal, pvIndex) in parameter_value" :key="pvIndex">
            <td>
                <workflow-invocation-data-contents v-if="['hda', 'hdca'].includes(elVal.src)" :data_item="elVal" />
                <span v-else> {{ elVal.hid }}: {{ elVal.name }} </span>
            </td>
        </tr>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";

import WorkflowInvocationDataContents from "components/WorkflowInvocationState/WorkflowInvocationDataContents";

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    components: {
        WorkflowInvocationDataContents,
    },
    props: {
        parameter_value: {
            type: Array,
        },
    },
    methods: {
        appRoot: function () {
            return getAppRoot();
        },
    },
    methods: {
        hidLabel(element) {
            return elVal.hid ? ` ${element.hid} : ${element.name}` : element.name;
        },
    },
};
</script>
