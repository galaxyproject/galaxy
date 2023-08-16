<script setup lang="ts">
import { computed, ref } from "vue";

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

const currentField = ref(0);

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

const currentVariant = computed(() => {
    if (variants.value && currentField.value < variants.value.length) {
        return variants.value[currentField.value];
    } else {
        return null;
    }
});

const variants = computed(() => {
    const flavorKey = props.flavor ? `${props.flavor}_` : "";
    const multipleKey = props.multiple ? `_${props.multiple}` : "";
    const variantKey = `${flavorKey}${props.type}${multipleKey}`;
    return Variants[variantKey];
});
</script>

<template>
    <div class="d-flex">
        <b-form-radio-group v-model="currentField" buttons>
            <b-form-radio v-for="(v, index) in variants" :key="index" :value="index">
                <span :class="`fa ${v.icon}`" />
            </b-form-radio>
        </b-form-radio-group>
        <FormDataSelect
            v-if="currentVariant"
            v-model="currentValue"
            class="w-100"
            :multiple="variants[currentField].multiple"
            :optional="optional"
            :options="options[variants[currentField].src]" />
    </div>
</template>
