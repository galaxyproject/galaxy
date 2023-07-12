<template>
    <b-input-group>
        <GInput v-model="filter" :placeholder="placeholder" />
        <b-input-group-append>
            <b-btn :disabled="!filter" @click="filter = ''"><i class="fa fa-times" /></b-btn>
        </b-input-group-append>
    </b-input-group>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import GInput from "@/component-library/GInput.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        GInput,
    },
    props: {
        value: {
            type: String,
            default: null,
        },
        title: {
            type: String,
            default: "",
        },
    },
    computed: {
        placeholder() {
            return `Type to Search ${this.title}`;
        },
        filter: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },
    },
};
</script>
