<script setup lang="ts">
export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
    selected: boolean;
}

export interface FormDrilldownProps {
    option: Option;
}

const props = defineProps<FormDrilldownProps>();
</script>
<template>
    <div class="form-drilldown-option">
        <b-form-checkbox v-model="props.option.selected">
            {{ props.option.name }}
            <form-drilldown-option v-for="option in props.option.options" :key="option.name" :option="option">
            </form-drilldown-option>
        </b-form-checkbox>
    </div>
</template>
