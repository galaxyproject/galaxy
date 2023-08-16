<script setup lang="ts">
import { computed } from "vue";

import type { DataOption, DataValue } from "./types";
import { Variants } from "./variants";

import FormDataSelect from "./FormDataSelect.vue";

interface DataOptions {
    hda: Array<DataOption>;
    hdca: Array<DataOption>;
}

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

const $emit = defineEmits(["input"]);

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

const variants = computed(() => {
    const flavorKey = props.flavor ? `${props.flavor}_` : "";
    const multipleKey = props.multiple ? `_${props.multiple}` : "";
    const variantKey = `${flavorKey}${props.type}${multipleKey}`;
    return Variants[variantKey];
});
</script>

<template>
    <div>
        <div v-for="(v, index) of variants" :key="index">
            <FormDataSelect
                v-model="currentValue"
                :multiple="v.multiple"
                :optional="optional"
                :options="options[v.src]" />
        </div>
    </div>
</template>
