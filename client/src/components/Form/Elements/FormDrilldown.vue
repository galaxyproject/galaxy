<script setup lang="ts">
import { computed } from "vue";
import FormDrilldownOption from "./FormDrilldownOption.vue";

export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
    selected: boolean;
}

export interface FormDrilldownProps {
    value?: string | string[];
    id: string;
    options: Array<Option>;
}

const props = withDefaults(defineProps<FormDrilldownProps>(), {
    value: "",
});

const hasOptions = computed(() => {
    return props.options.length > 0;
});

let currentValue: string[] = [];

function addToSelected(n: string, v: boolean) {
    if (v == true) {
        currentValue.push(n);
    } else if (v == false) {
        const index = currentValue.indexOf(n);
        currentValue.splice(index, 1);
    }
    emit("input", currentValue);
    console.log(":CV:", currentValue);
}

//currentValue will be computed array of selected values
//need to implement selectAll

const emit = defineEmits<{
    (e: "input", value: string[]): void;
}>();

// const currentValue =  computed({
//     get: () => {
//         return selected;
//     },
//     set: (selected) => {
//         emit("input", selected);
//     },
// });
</script>

<template>
    <div v-if="hasOptions">
        <ul v-for="option in options" :key="option.name" class="options">
            <form-drilldown-option :option="option" :depth="0" :handle-click="addToSelected"></form-drilldown-option>
        </ul>
    </div>
</template>
