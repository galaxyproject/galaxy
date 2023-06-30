<script setup lang="ts">
import { computed } from "vue";
import FormSelect from "./FormDataSelect.vue";
import type { DataOption, DataOptions, DataValue } from "./types";

const $emit = defineEmits(["input"]);

const props = withDefaults(
    defineProps<{
        multiple?: boolean;
        optional?: boolean;
        options: DataOptions;
        value?: DataValue;
        extensions?: Array<string>;
        type?: string;
        flavor?: string;
        tag?: string;
    }>(),
    {
        multiple: false,
        optional: false,
        value: null,
        extensions: () => [],
        type: "data",
        flavor: null,
        tag: null,
    }
);

const currentValue = computed({
    get: () => {
        console.log("in", props.value.values);
        return props.value.values;
    },
    set: (val) => {
        console.log("out", val);
        $emit("input", val);
    },
});
</script>

<template>
    <form-select v-model="currentValue" :multiple="multiple" :optional="optional" :options="options.hda" />
</template>
