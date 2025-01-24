<script setup lang="ts">
import { BInputGroup } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { type ValidFilter } from "@/utils/filtering";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

type FilterType = string | boolean | undefined;

interface Props {
    name: string;
    identifier: any;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterType;
    };
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", name: string, value: FilterType): void;
}>();

const propValue = computed(() => props.filters[props.name]);

const localValue = ref(propValue.value);

watch(
    () => localValue.value,
    (newFilter) => {
        emit("change", props.name, newFilter);
    }
);

watch(
    () => propValue.value,
    (newFilter) => {
        localValue.value = newFilter;
    }
);
</script>

<template>
    <div>
        <small>Filter by {{ props.filter.placeholder }}:</small>

        <BInputGroup :id="`${identifier}-advanced-filter-${props.name}`">
            <StatelessTags
                :value="localValue"
                :placeholder="`any ${props.filter.placeholder}`"
                @input="(tags) => (localValue = tags)" />
        </BInputGroup>
    </div>
</template>
