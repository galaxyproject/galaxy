<template>
    <b-input-group>
        <b-input v-model="value" placeholder="Type to Search" />
        <b-input-group-append>
            <b-btn :disabled="!value" @click="value = ''">Clear</b-btn>
        </b-input-group-append>
    </b-input-group>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: ["value"],
    watch: {
        value: function(new_value) {
            this.$emit("input", new_value);
        }
    }
};
</script>
