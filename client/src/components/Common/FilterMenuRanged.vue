<script setup lang="ts">
import { computed, type PropType, ref, watch } from "vue";

import { ValidFilter } from "@/utils/filtering";

const props = defineProps({
    name: { type: String, required: true },
    filter: { type: Object as PropType<ValidFilter<any>>, required: true },
    filters: { type: Object, required: true },
    error: { type: Object, default: null },
    identifier: { type: String, required: true },
});

const emit = defineEmits<{
    (e: "change", name: string, value: string): void;
    (e: "on-enter"): void;
    (e: "on-esc"): void;
}>();

const localNameLt = computed(() => `${props.name}_lt`);
const localNameGt = computed(() => `${props.name}_gt`);
const valueLt = computed(() => props.filters[localNameLt.value]);
const valueGt = computed(() => props.filters[localNameGt.value]);

const localValueGt = ref(valueGt.value);
const localValueLt = ref(valueLt.value);

watch(
    () => localValueGt.value,
    (newFilter: string) => {
        emit("change", localNameGt.value, newFilter);
    }
);
watch(
    () => localValueLt.value,
    (newFilter: string) => {
        emit("change", localNameLt.value, newFilter);
    }
);
watch(
    () => valueGt.value,
    (newFilter: string) => {
        localValueGt.value = newFilter;
    }
);
watch(
    () => valueLt.value,
    (newFilter: string) => {
        localValueLt.value = newFilter;
    }
);

const isDateType = computed(() => props.filter.type == Date);

function hasError(field: string) {
    if (props.error && props.error.index == field) {
        return props.error.typeError || props.error.msg;
    }
    return "";
}

function localPlaceholder(comp: "gt" | "lt") {
    if (comp == "gt") {
        const field = isDateType.value ? "after" : "greater";
        return `${props.filter.placeholder} ${field}`;
    } else {
        const field = isDateType.value ? "before" : "lower";
        return `${props.filter.placeholder} ${field}`;
    }
}
</script>

<template>
    <div>
        <small>Filter by {{ props.filter.placeholder }}:</small>
        <b-input-group>
            <!---------------------------- GREATER THAN ---------------------------->
            <b-form-input
                :id="`${props.identifier}-advanced-filter-${localNameGt}`"
                v-model="localValueGt"
                v-b-tooltip.focus.v-danger="hasError(localNameGt)"
                size="sm"
                :state="hasError(localNameGt) ? false : null"
                :placeholder="localPlaceholder('gt')"
                @keyup.enter="emit('on-enter')"
                @keyup.esc="emit('on-esc')" />
            <b-input-group-append v-if="isDateType">
                <b-form-datepicker v-model="localValueGt" reset-button button-only size="sm" />
            </b-input-group-append>
            <!--------------------------------------------------------------------->

            <!---------------------------- LESSER THAN ---------------------------->
            <b-form-input
                :id="`${props.identifier}-advanced-filter-${localNameLt}`"
                v-model="localValueLt"
                v-b-tooltip.focus.v-danger="hasError(localNameLt)"
                size="sm"
                :state="hasError(localNameLt) ? false : null"
                :placeholder="localPlaceholder('lt')"
                @keyup.enter="emit('on-enter')"
                @keyup.esc="emit('on-esc')" />
            <b-input-group-append v-if="isDateType">
                <b-form-datepicker v-model="localValueLt" reset-button button-only size="sm" />
            </b-input-group-append>
            <!--------------------------------------------------------------------->
        </b-input-group>
    </div>
</template>
