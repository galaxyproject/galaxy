<template>
    <VueMultiselect
        class="select-basic"
        :close-on-select="!multiple"
        :options="options"
        :multiple="multiple"
        :placeholder="placeholder || 'Select an option'"
        :value="selectedValue"
        deselect-label=""
        label="text"
        select-label=""
        track-by="id"
        @input="onInput" />
</template>

<script setup>
import { computed } from "vue";
import VueMultiselect from "vue-multiselect";

const props = defineProps({
    value: { required: false },
    multiple: { type: Boolean, default: false },
    options: { type: Array, default: () => [] },
    placeholder: { type: String, default: null },
});

const emit = defineEmits(["input"]);

const selectedValue = computed(() => {
    if (!props.value) {
        return props.multiple ? [] : null;
    }
    if (props.multiple) {
        return props.options.filter((opt) => props.value.includes(opt.id));
    }
    const singleValue = Array.isArray(props.value) ? props.value[0] : props.value;
    return props.options.find((opt) => opt.id === singleValue) || null;
});

const onInput = (selected) => {
    const outputValue = props.multiple ? selected.map((opt) => opt.id) : selected ? selected.id : null;
    emit("input", outputValue);
};
</script>
