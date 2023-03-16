<script setup lang="ts">
import { computed } from "vue";
import FormDrilldownOption from "./FormDrilldownOption.vue";

export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
}

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

function addToSelected(n: string, v: boolean) {
    /*if (v == true) {
        currentValue.push(n);
    } else if (v == false) {
        const index = currentValue.indexOf(n);
        currentValue.splice(index, 1);
    }
    emit("input", currentValue); //HELP problem with this is that once a checkbox is checked, if you uncheck it no longer requires something is checked, and you're able to send an empty array
    console.log(":CV:", currentValue);*/
}

//TODO implement selectAll
</script>

<template>
    <div v-if="hasOptions">
        <form-drilldown-option :options="options" :handle-click="addToSelected" />
    </div>
</template>
