<script setup lang="ts">
import { computed, ref } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";
import type { Option } from "./types.js";

export interface Props {
    currentValue: string[];
    option: Option;
    handleClick: Function;
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
            <span v-if="showChildren" class="fa fa-minus-square" />
            <span v-else class="fa fa-plus-square" />
        </span>
        <b-form-checkbox class="d-inline" :checked="isChecked" @change="handleClick(option.value)" />
        {{ option.name }}
        <form-drilldown-list
            v-if="hasOptions"
            v-show="showChildren"
            :current-value="currentValue"
            :options="option.options"
            :handle-click="handleClick" />
    </li>
</template>
