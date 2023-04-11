<script setup lang="ts">
import { computed, ref } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";
import type { Option } from "./types.js";

export interface Props {
    currentValue: string[];
    option: Option;
    handleClick: Function;
    multiple: boolean;
}

const props = defineProps<Props>();

const showChildren = ref(false);

const hasOptions = computed(() => {
    return props.option.options.length > 0;
});

const isChecked = computed(() => {
    const optionValue = props.option.value;
    return props.currentValue.indexOf(optionValue) !== -1;
});

function toggleChildren() {
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
            class="d-inline drilldown-option"
            :checked="isChecked"
            @change="handleClick(option.value)" />
        <b-form-radio
            v-else
            class="d-inline"
            :selected="isChecked"
            name="selectedOption"
            @change="handleClick(option.value)" />
        {{ option.name }}
        <form-drilldown-list
            v-if="hasOptions"
            v-show="showChildren"
            :current-value="currentValue"
            :multiple="props.multiple"
            :options="option.options"
            :handle-click="handleClick" />
    </li>
</template>
