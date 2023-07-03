<template>
    <b-table small caption-top :fields="['label', 'parameter_value']" :items="parameters" />
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    props: {
        parameters: { type: Array, required: true },
    },
};
</script>
