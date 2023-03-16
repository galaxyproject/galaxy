<script setup lang="ts">
import { computed, ref } from "vue";

export interface Option {
    name: string;
    value: string;
    options: Array<Option>;
}

export interface FormDrilldownProps {
    options: Array<Option>;
    handleClick: Function;
}

const props = defineProps<FormDrilldownProps>();

const showChildren = ref(false);

const hasOptions = computed(() => {
    return props.options.length > 0;
});

function toggleChildren() {
    showChildren.value = !showChildren.value;
}
</script>

<template>
    <div class="form-drilldown-option">
        <ul v-for="option in options" :key="option.name" class="options">
            {{ option.name }}
        </ul>
    </div>
</template>
