<script setup lang="ts">
import type { Option } from "./utilities";

import FormDrilldownOption from "./FormDrilldownOption.vue";

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
            <FormDrilldownOption
                :current-value="currentValue"
                :handle-click="handleClick"
                :multiple="multiple"
                :option="option" />
        </div>
    </div>
</template>
