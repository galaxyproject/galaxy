<script setup lang="ts">
import type { Option } from "./utilities";

import FormDrilldownOption from "./FormDrilldownOption.vue";

defineProps<{
    currentValue: string[];
    handleClick: Function;
    multiple: boolean;
    showIcons?: boolean;
    options: Array<Option>;
}>();
</script>

<template>
    <div class="ui-drilldown">
        <div v-for="option in options" :key="option.name" class="descendant-lines">
            <FormDrilldownOption
                :show-icons="showIcons"
                :current-value="currentValue"
                :handle-click="handleClick"
                :multiple="multiple"
                :option="option" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";
.ui-drilldown {
    $ui-drilldown-border: 0.5px solid $gray-500;

    /* selector: all except first nested drilldown */
    & > * .descendant-lines {
        border-left: $ui-drilldown-border;
    }
}
</style>
