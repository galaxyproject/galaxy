<template>
    <GInput
        ref="input"
        v-model="slugInput"
        class="d-inline w-auto h-auto px-1 py-0"
        @change="onChange"
        @keydown.enter="onChange"
        @keydown.esc="onCancel" />
</template>
<script>
import GInput from "@/component-library/GInput.vue";

export default {
    components: {
        GInput,
    },
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
