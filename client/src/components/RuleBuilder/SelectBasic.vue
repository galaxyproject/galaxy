<template>
    <select class="select-basic" :value="value" :multiple="multiple" @change="onChange">
        <option v-if="placeholder" value="" disabled selected>{{ placeholder }}</option>
        <option v-for="option in options" :key="option.id" :value="option.id">
            {{ option.text }}
        </option>
    </select>
</template>

<script>
export default {
    props: {
        value: { required: false },
        multiple: { type: Boolean, default: false },
        options: {
            type: Array,
            default: () => [],
            validator: (options) => options.every((opt) => "id" in opt && "text" in opt),
        },
        placeholder: { type: String, default: null },
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
