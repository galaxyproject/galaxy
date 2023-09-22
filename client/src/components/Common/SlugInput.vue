<template>
    <b-input
        ref="input"
        v-model="slugInput"
        class="d-inline w-auto h-auto px-1 py-0"
        @change="onChange"
        @keydown.enter="onChange"
        @keydown.esc="onCancel" />
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        slug: {
            type: String,
            required: true,
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
            const slugFormatted = this.slugInput
                .replace(/\s+/g, "-")
                .replace(/[^a-zA-Z0-9-]/g, "")
                .toLowerCase();
            this.$emit("onChange", slugFormatted);
        },
        onCancel() {
            this.$emit("onChange", this.slug);
        },
    },
};
</script>
