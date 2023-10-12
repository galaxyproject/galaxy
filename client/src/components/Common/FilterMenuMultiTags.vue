<script setup lang="ts">
import { computed, type PropType, ref, watch } from "vue";

import { ValidFilter } from "@/utils/filtering";

import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

const props = defineProps({
    name: { type: String, required: true },
    filter: { type: Object as PropType<ValidFilter<any>>, required: true },
    filters: { type: Object, required: true },
    identifier: { type: String, required: true },
});

const emit = defineEmits<{
    (e: "change", name: string, value: string): void;
}>();

const propValue = computed(() => props.filters[props.name]);

const localValue = ref(propValue.value);

watch(
    () => localValue.value,
    (newFilter: string) => {
        emit("change", props.name, newFilter);
    }
);
watch(
    () => propValue.value,
    (newFilter: string) => {
        localValue.value = newFilter;
    }
);
</script>

<template>
    <div>
        <small>Filter by {{ props.filter.placeholder }}:</small>
        <b-input-group :id="`${identifier}-advanced-filter-${props.name}`">
            <StatelessTags
                :value="localValue"
                :placeholder="`any ${props.filter.placeholder}`"
                @input="(tags) => (localValue = tags)" />
        </b-input-group>
    </div>
</template>
