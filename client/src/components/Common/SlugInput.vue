<template>
    <b-input
        v-model="slugInput"
        @change="onChange"
        @keydown.enter="onChange"
        @keydown.esc="onCancel"
        class="d-inline w-auto h-auto px-1 py-0"
        ref="input"
    />
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        slug: {
            type: String,
        },
    },
    data() {
        return {
            slugInput: this.slug,
        };
    },
    mounted() {
        this.$refs.input.select();
    },
    methods: {
        onChange() {
            this.$emit("onChange", this.slugInput);
        },
        onCancel() {
            this.$emit("onChange", this.slug);
        },
    },
};
</script>
