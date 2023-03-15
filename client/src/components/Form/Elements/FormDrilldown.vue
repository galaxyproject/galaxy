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

let currentValue: string[] = []; //was called selected, when attempting to use computed currentValue

function addToSelected(n: string, v: boolean) {
    if (v == true) {
        currentValue.push(n);
    } else if (v == false) {
        const index = currentValue.indexOf(n);
        currentValue.splice(index, 1);
    }
    emit("input", currentValue); //HELP problem with this is that once a checkbox is checked, if you uncheck it no longer requires something is checked, and you're able to send an empty array
    console.log(":CV:", currentValue);
}

//TODO implement selectAll

const emit = defineEmits<{
    (e: "input", value: string[]): void;
}>();

// HELP:
// can't use this computed as is, because, I can't push to computed (like I can with an array)
// and when I simply set the currentValue to what's in the array I curated above
// it dowesn't update and emit the changing values, and just remains an empty array

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
