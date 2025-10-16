<template>
    <VueMultiselect
        class="select-basic"
        :value="selectedValue"
        :options="options"
        :multiple="multiple"
        :placeholder="placeholder || 'Select an option'"
        track-by="id"
        label="text"
        @input="onInput" />
</template>

<script>
import VueMultiselect from "vue-multiselect";

export default {
    components: { VueMultiselect },
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
    computed: {
        selectedValue() {
            if (!this.value) {
                return this.multiple ? [] : null;
            }
            if (this.multiple) {
                return this.options.filter((opt) => this.value.includes(opt.id));
            }
            // Handle both single value and array for single-select
            const singleValue = Array.isArray(this.value) ? this.value[0] : this.value;
            return this.options.find((opt) => opt.id === singleValue) || null;
        },
    },
    methods: {
        onInput(selected) {
            const value = this.multiple ? selected.map((opt) => opt.id) : selected ? selected.id : null;
            this.$emit("input", value);
        },
    },
};
</script>
