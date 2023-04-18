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
    multiple: true,
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

function handleClick(value: string): void {
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
    } else {
        emit("input", value);
    }
}

function selectAll(selected: boolean): void {
    const newValue: string[] = [];
    if (selected) {
        let options = null;
        const stack: Array<Array<Option>> = [props.options];
        while ((options = stack.pop())) {
            options.forEach((option) => {
                if (option.value) {
                    newValue.push(option.value);
                }
                if (option.options.length > 0) {
                    stack.push(option.options);
                }
            });
        }
    }
    emit("input", newValue.length === 0 ? null : newValue);
}
</script>

<template>
    <div v-if="hasOptions">
        <b-form-checkbox
            v-if="props.multiple"
            class="d-inline select-all-checkbox"
            :selected="false"
            @change="selectAll" />
        Select/Deselect All
        <form-drilldown-list
            :multiple="props.multiple"
            :current-value="currentValue"
            :options="options"
            :handle-click="handleClick" />
    </div>
</template>
