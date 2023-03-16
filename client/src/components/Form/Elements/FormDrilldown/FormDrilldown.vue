<script setup lang="ts">
import { computed } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";
import type { Option } from "./types.js";

export interface FormDrilldownProps {
    id: string;
    value?: string | string[];
    options: Array<Option>;
}

const props = withDefaults(defineProps<FormDrilldownProps>(), {
    value: null,
});

const emit = defineEmits<{
    (e: "input", value: string[]): void;
}>();

const hasOptions = computed(() => {
    return props.options.length > 0;
});

const currentValue = computed({
    get: (): string[] => {
        if (Array.isArray(props.value)) {
            return props.value;
        } else {
            return [props.value];
        }
    },
    set: (newValue: string[]): void => {
        emit("input", newValue);
    },
});

function handleClick(value: string) {
    console.log(value);
    const newValue = currentValue.value.slice();
    const index = newValue.indexOf(value);
    if (index !== -1) {
        newValue.splice(index, 1);
    } else {
        newValue.push(value);
    }
    emit("input", newValue);
}

//TODO implement selectAll
</script>

<template>
    <div v-if="hasOptions">
        <form-drilldown-list :current-value="currentValue" :options="options" :handle-click="handleClick" />
    </div>
</template>
