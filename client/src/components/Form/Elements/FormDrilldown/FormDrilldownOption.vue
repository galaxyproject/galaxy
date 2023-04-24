<script setup lang="ts">
import { computed, onMounted, ref, type ComputedRef } from "vue";
import { BFormCheckbox, BFormRadio } from "bootstrap-vue";
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
            <i v-if="showChildren" class="fa fa-minus-square" />
            <i v-else class="fa fa-plus-square" />
        </b-button>
        <component
            :is="isComponent"
            class="drilldown-option d-inline"
            value="true"
            :checked="isChecked"
            @change="handleClick(option.value)">
            {{ option.name }}
        </component>
        <form-drilldown-list
            v-if="hasOptions"
            v-show="showChildren"
            class="pl-5"
            :current-value="currentValue"
            :multiple="multiple"
            :options="option.options"
            :handle-click="handleClick" />
    </div>
</template>
