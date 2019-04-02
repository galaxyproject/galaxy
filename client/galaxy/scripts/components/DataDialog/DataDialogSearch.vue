<template>
    <b-input-group>
        <b-input v-model="filter" placeholder="Type to Search" />
        <b-input-group-append>
            <b-btn :disabled="!filter" @click="filter = ''">Clear</b-btn>
        </b-input-group-append>
    </b-input-group>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: ["value"],
    data() {
        return {
            filter: null
        };
    },
    watch: {
        filter: function(value) {
            this.$emit("input", value);
        }
    }
};
</script>
