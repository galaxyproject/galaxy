<template>
    <select class="basic-select" :value="value" :multiple="multiple" @change="onChange">
        <slot></slot>
    </select>
</template>

<script>
export default {
    props: {
        value: { required: false },
        multiple: { type: Boolean, default: false },
    },
    methods: {
        onChange(event) {
            const selected = this.multiple
                ? Array.from(event.target.selectedOptions).map((o) => o.value)
                : event.target.value;
            this.$emit("input", selected);
        },
    },
};
</script>
