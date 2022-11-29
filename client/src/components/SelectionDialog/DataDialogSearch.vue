<template>
    <b-input-group>
        <b-input v-model="filter" :placeholder="placeholder" />
        <b-input-group-append>
            <b-btn :disabled="!filter" @click="filter = ''"><FontAwesomeIcon icon="fa-times" /></b-btn>
        </b-input-group-append>
    </b-input-group>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes);

Vue.use(BootstrapVue);

export default {
    components: { FontAwesomeIcon },
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
