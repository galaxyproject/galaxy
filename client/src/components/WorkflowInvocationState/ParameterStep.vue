<template>
    <GTable :fields="['label', 'parameter_value']" :items="parameters" caption-top small />
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { GTable } from "@/component-library";

Vue.use(BootstrapVue);

export default {
    components: {
        GTable,
    },
    props: {
        parameters: { type: Array, required: true },
    },
};
</script>
