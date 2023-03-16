<script setup lang="ts">
import { computed, ref } from "vue";
import FormDrilldownList from "./FormDrilldownList.vue";

export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
}

export interface Props {
    option: Option;
    handleClick: Function;
}

const props = defineProps<Props>();

const showChildren = ref(false);

const hasOptions = computed(() => {
    return props.option.options.length > 0;
});

function toggleChildren() {
    showChildren.value = !showChildren.value;
}
</script>

<template>
    <li>
        <span v-if="hasOptions" @click="toggleChildren">
            <span v-if="showChildren" class="fa fa-plus-square" />
            <span v-else class="fa fa-minus-square" />
        </span>
        <b-form-checkbox class="d-inline" />
        {{ option.name }}
        <form-drilldown-list v-show="showChildren" :options="option.options" :handle-click="handleClick" />
    </li>
</template>
