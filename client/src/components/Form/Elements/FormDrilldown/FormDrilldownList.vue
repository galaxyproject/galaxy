<script setup lang="ts">
import FormDrilldownOption from "./FormDrilldownOption.vue";
import type { Option } from "./utilities";

defineProps<{
    currentValue: string[];
    handleClick: Function;
    multiple: boolean;
    options: Array<Option>;
}>();
</script>

<template>
    <div>
        <div v-for="option in options" :key="option.name" class="ui-drilldown">
            <form-drilldown-option
                :current-value="currentValue"
                :handle-click="handleClick"
                :multiple="multiple"
                :option="option" />
        </div>
    </div>
</template>
