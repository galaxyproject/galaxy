<script setup lang="ts">
import { BFormCheckbox, BFormRadio } from "bootstrap-vue";
import { computed, type ComputedRef, onMounted, ref } from "vue";

import { getAllValues, type Option } from "./utilities";

import FormDrilldownList from "./FormDrilldownList.vue";

const props = defineProps<{
    currentValue: string[];
    option: Option;
    handleClick: Function;
    multiple: boolean;
}>();

const showChildren = ref(false);

const hasOptions: ComputedRef<boolean> = computed(() => {
    return props.option.options.length > 0;
});

// indicates if the value has been selected or not
const isChecked: ComputedRef<boolean> = computed(() => {
    const optionValue = props.option.value;
    return props.currentValue.includes(optionValue);
});

// determine required input element type
const isComponent = computed(() => {
    return props.multiple ? BFormCheckbox : BFormRadio;
});

function toggleChildren(): void {
    showChildren.value = !showChildren.value;
}

function toggleInitialization(): void {
    const childValues = getAllValues(props.option.options);
    for (const childValue of childValues) {
        if (props.currentValue.includes(childValue)) {
            showChildren.value = true;
            break;
        }
    }
}
onMounted(() => {
    toggleInitialization();
});
</script>

<template>
    <div>
        <b-button v-if="hasOptions" variant="link" class="btn p-0" @click="toggleChildren">
            <i v-if="showChildren" class="fa fa-caret-down align-checkbox" />
            <i v-else class="fa fa-caret-right align-checkbox" />
        </b-button>
        <span v-if="!hasOptions" class="align-indent"></span>
        <component
            :is="isComponent"
            class="drilldown-option d-inline"
            value="true"
            :checked="isChecked"
            @change="handleClick(option.value, $event)">
            {{ option.name }}
        </component>
        <FormDrilldownList
            v-if="hasOptions"
            v-show="showChildren"
            class="indent"
            :current-value="currentValue"
            :multiple="multiple"
            :options="option.options"
            :handle-click="handleClick" />
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";
.ui-drilldown {
    $ui-drilldown-padding: 1rem;
    $ui-drilldown-border: 0.5px solid $gray-500;

    .indent {
        padding-left: calc($ui-drilldown-padding + $ui-drilldown-padding/2);
    }
    .align-indent {
        display: inline-block;
        width: $ui-drilldown-padding;
        border-bottom: $ui-drilldown-border;
    }
    .align-checkbox {
        width: $ui-drilldown-padding;
    }
}
</style>
