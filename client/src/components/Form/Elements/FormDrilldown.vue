<script setup lang="ts">
import { computed } from "vue";
import FormDrilldownOption from "./FormDrilldownOption.vue"

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
//currentValue will be computed array of selected values
//need to implement selectAll

</script>

<template>
    <div v-if="hasOptions">
        <div v-for="option in options" :key="option.name" class="options">
            <form-drilldown-option :option="option" :depth="0"></form-drilldown-option>
        </div>
    </div>
</template>
