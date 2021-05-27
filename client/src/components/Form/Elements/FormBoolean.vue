<template>
    <b-form-checkbox v-model="currentValue" size="lg" switch @onChange="onChange" />
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        value: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            currentValue: this.value,
        };
    },
    watch: {
        value(newValue) {
            this.currentValue = newValue;
        },
    },
    methods: {
        onChange() {
            this.$emit("onChange", this.currentValue);
        },
    },
};
</script>
