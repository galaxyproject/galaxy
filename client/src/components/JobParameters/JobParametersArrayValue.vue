<template>
    <div>
        <ul style="padding-inline-start: 25px">
            <li v-for="(elVal, pvIndex) in parameter_value" :key="pvIndex">
                <span v-if="elVal.src == 'hda'">
                    <a :href="appRoot() + 'datasets/' + elVal.id + '/show_params'">
                        {{ elVal.hid }}: {{ elVal.name }}
                    </a>
                </span>
                <span v-else> {{ elVal.hid }}: {{ elVal.name }} </span>
            </li>
        </ul>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";

import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
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
};
</script>
