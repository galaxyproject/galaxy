<script setup lang="ts">
import { computed, ref } from "vue";
import FormDrilldownOption from "./FormDrilldownOption.vue";

export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
}

export interface Props {
    options: Array<Option>;
    handleClick: Function;
}

const props = defineProps<Props>();
</script>

<template>
    <div>
        <ul v-for="option in options" :key="option.name" class="ui-drilldown">
            <form-drilldown-option :option="option" :handle-click="handleClick" />
        </ul>
    </div>
</template>

<style>
.ui-drilldown {
    list-style-type: none;
}
</style>
