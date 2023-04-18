<script setup lang="ts">
import { computed, ref, type ComputedRef } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";
import type { Option } from "./utilities";

export interface Props {
    currentValue: string[];
    option: Option;
    handleClick: Function;
    multiple: boolean;
}

const props = defineProps<Props>();

const showChildren = ref(false);

const hasOptions: ComputedRef<boolean> = computed(() => {
    return props.option.options.length > 0;
});

// indicates if the value has been selected or not (required for checkbox display)
const isChecked: ComputedRef<boolean> = computed(() => {
    const optionValue = props.option.value;
    return props.currentValue.includes(optionValue);
});

// provides a single value, which is either null or a non-empty string (required for radio display)
const singleValue = computed({
    get(): string | null {
        const value: string[] = props.currentValue;
        return value.length > 0 ? value[0] || null : null;
    },
    set() {},
});

function toggleChildren(): void {
    showChildren.value = !showChildren.value;
}
</script>

<template>
    <li>
        <span v-if="hasOptions" @click="toggleChildren">
            <icon v-if="showChildren" fixed-width icon="minus-square" />
            <icon v-else fixed-width icon="plus-square" />
        </span>
        <b-form-checkbox
            v-if="multiple"
            class="drilldown-option d-inline"
            :checked="isChecked"
            @change="handleClick(option.value)">
            {{ option.name }}
        </b-form-checkbox>
        <b-form-radio
            v-else
            v-model="singleValue"
            class="drilldown-option d-inline"
            :value="option.value"
            @change="handleClick(option.value)">
            {{ option.name }}
        </b-form-radio>
        <form-drilldown-list
            v-if="hasOptions"
            v-show="showChildren"
            :current-value="currentValue"
            :multiple="props.multiple"
            :options="option.options"
            :handle-click="handleClick" />
    </li>
</template>
