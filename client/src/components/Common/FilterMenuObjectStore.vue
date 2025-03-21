<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useSelectableObjectStores } from "@/composables/useObjectStores";
import { type ValidFilter } from "@/utils/filtering";

import FilterObjectStoreLink from "./FilterObjectStoreLink.vue";

type FilterType = string | undefined;

interface Props {
    name: string;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterType;
    };
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", name: string, value: FilterType): void;
}>();

const propValue = computed<FilterType>(() => props.filters[props.name]);

const localValue = ref<FilterType>(propValue.value);

watch(
    () => localValue.value,
    (newFilter: FilterType) => {
        emit("change", props.name, newFilter);
    }
);
watch(
    () => propValue.value,
    (newFilter: FilterType) => {
        localValue.value = newFilter;
    }
);

const { selectableObjectStores, hasSelectableObjectStores } = useSelectableObjectStores();

function onChange(value: FilterType) {
    localValue.value = value;
}
</script>

<template>
    <div v-if="hasSelectableObjectStores">
        <small>按存储源过滤：</small>
        <FilterObjectStoreLink :object-stores="selectableObjectStores || []" :value="localValue" @change="onChange" />
    </div>
</template>