<script setup lang="ts">
import FormDrilldownOption from "./FormDrilldownOption.vue";
import type { Option } from "./utilities";

export interface Props {
    currentValue: string[];
    options: Array<Option>;
    handleClick: Function;
    multiple: boolean;
}

const props = defineProps<Props>();
</script>

<template>
    <div>
        <ul v-for="option in props.options" :key="option.name" class="ui-drilldown m-0">
            <form-drilldown-option
                :multiple="props.multiple"
                :current-value="currentValue"
                :option="option"
                :handle-click="handleClick" />
        </ul>
    </div>
</template>

<style>
.ui-drilldown {
    list-style-type: none;
}
</style>
