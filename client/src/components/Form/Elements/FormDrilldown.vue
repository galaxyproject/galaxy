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
// export interface SelectedArray {
//     selected: string[];
// }

const props = withDefaults(defineProps<FormDrilldownProps>(), {
    value: "",
});

const hasOptions = computed(() => {
    return props.options.length > 0;
});

// let selected: SelectedArray = {
//     selected: [],
// };

// function addToSelected(n: string, v: boolean) {
//     if (v == true) {
//         selected.selected.push(n);
//     } else if (v == false) {
//         const index = selected.selected.indexOf(n);

//         const x = selected.selected.splice(index, 1);
//     }
//     console.log(":selectedArray:", selected.selected)
// }

//currentValue will be computed array of selected values
//need to implement selectAll

const emit = defineEmits<{
    (e: "input", value: string[]): void;
}>();

const currentValue = computed({
    get: () => {
        
    },
    set: (newValue) => {
        

        // if (newValue.length === 0) {
        //     selectAll.value = false;
        //     indeterminate.value = false;
        // } else if (newValue.length === props.options.length) {
        //     selectAll.value = true;
        //     indeterminate.value = false;
        // } else {
        //     indeterminate.value = true;
        // }
    },
});
</script>

<template>
    <div v-if="hasOptions">
        <ul v-for="option in options" :key="option.name" class="options">
            <form-drilldown-option
                :option="option"
                :depth="0"
                @selected="currentValue.set"></form-drilldown-option>
        </ul>
    </div>
</template>
