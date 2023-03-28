<script setup lang="ts">
import { computed } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";
import type { Option } from "./types.js";

export interface FormDrilldownProps {
    id: string;
    value?: string | string[];
    options: Array<Option>;
    multiple: boolean;
}

const props = withDefaults(defineProps<FormDrilldownProps>(), {
    value: null,
    multiple: false,
});

const emit = defineEmits<{
    (e: "input", value: string[] | null | string): void;
}>();

const hasOptions = computed(() => {
    return props.options.length > 0;
});

const currentValue = computed({
    get: (): string[] => {
        if (props.value === null || props.value === "") {
            return [];
        } else if (Array.isArray(props.value)) {
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
    if (props.multiple) {
        const newValue = currentValue.value.slice();
        const index = newValue.indexOf(value);
        if (index !== -1) {
            newValue.splice(index, 1);
        } else {
            newValue.push(value);
        }
        if (newValue.length === 0) {
            emit("input", null);
        } else {
            emit("input", newValue);
        }
    }
    if (!props.multiple) {
        emit("input", value);
    }
    
}

//TODO implement selectAll
</script>

<template>
    <div v-if="hasOptions">
        <form-drilldown-list
            :multiple="props.multiple"
            :current-value="currentValue"
            :options="options"
            :handle-click="handleClick" />
    </div>
</template>
