<script setup lang="ts">
import { computed, ref } from "vue";

export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
    selected: boolean;
}

export interface FormDrilldownProps {
    option: Option;
    depth: number;
}
function toggleChildren() {
    showChildren.value = !showChildren.value;
}

const showChildren = ref(false);

const props = defineProps<FormDrilldownProps>();

const hasOptions = computed(() => {
    return props.option.options.length > 0;
});
const indent = computed(() => {
    return {transform: `translate(${props.depth * 25}px)`, "list-style-type": "none"}
});
</script>
<template>
    <div class="form-drilldown-option">
        <li :class="{ 'ui-drilldown-subgroup': depth > 0 }" :style="indent">
            <span
                v-if="hasOptions"
                @click="toggleChildren"
                class="ui-drilldown-button"
                :class="{ 'fa fa-plus-square': !showChildren, 'fa fa-minus-square': showChildren }" />
            <b-form-checkbox v-model="props.option.selected" style="display: inline-block" />
            {{ props.option.name }}
            </li>
            <form-drilldown-option
                v-show="showChildren"
                v-for="option in props.option.options"
                :key="option.name"
                :option="option"
                :depth="depth + 1">
            </form-drilldown-option>
    </div>
</template>
