<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { ValidFilter } from "@/utils/filtering";

import FilterObjectStoreLink from "./FilterObjectStoreLink.vue";

type FilterType = string | boolean | undefined;

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

const store = useObjectStoreStore();
const { selectableObjectStores } = storeToRefs(store);

const hasObjectStores = computed(() => {
    return selectableObjectStores.value && selectableObjectStores.value.length > 0;
});

function onChange(value: string | null) {
    localValue.value = (value || undefined) as FilterType;
}
</script>

<template>
    <div v-if="hasObjectStores">
        <small>Filter by storage source:</small>
        <FilterObjectStoreLink :object-stores="selectableObjectStores" :value="localValue" @change="onChange" />
    </div>
</template>
