<template>
    <GInputGroup>
        <GInput v-model="filter" :placeholder="placeholder" />
        <GInputGroupAppend>
            <b-btn :disabled="!filter" @click="filter = ''"><i class="fa fa-times" /></b-btn>
        </GInputGroupAppend>
    </GInputGroup>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import GInput from "@/component-library/GInput.vue";
import GInputGroup from "@/component-library/GInputGroup.vue";
import GInputGroupAppend from "@/component-library/GInputGroupAppend.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        GInputGroup,
        GInputGroupAppend,
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
