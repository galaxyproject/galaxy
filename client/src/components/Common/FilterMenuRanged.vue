<script setup lang="ts">
import { BFormDatepicker, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { type ErrorType, type ValidFilter } from "@/utils/filtering";

type FilterType = string | boolean | undefined;

interface Props {
    name: string;
    identifier: any;
    error?: ErrorType;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterType;
    };
    disabled?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "change", name: string, value: FilterType): void;
    (e: "on-enter"): void;
    (e: "on-esc"): void;
}>();

const localNameLt = computed(() => `${props.name}_lt`);
const localNameGt = computed(() => `${props.name}_gt`);
const valueLt = computed(() => props.filters[localNameLt.value]);
const valueGt = computed(() => props.filters[localNameGt.value]);

const localValueGt = ref(valueGt.value);
const localValueLt = ref(valueLt.value);

const isDateType = computed(() => props.filter.type == Date);

function hasError(field: string) {
    if (props.error && props.error.index == field) {
        return props.error.typeError || props.error.msg;
    }
    return "";
}

function localPlaceholder(comp: "gt" | "lt") {
    if (comp == "gt") {
        const field = isDateType.value ? "after" : "greater than";
        return `${field} ${props.filter.placeholder}`;
    } else {
        const field = isDateType.value ? "before" : "lower than";
        return `${field} ${props.filter.placeholder}`;
    }
}

watch(
    () => localValueGt.value,
    (newFilter) => {
        emit("change", localNameGt.value, newFilter);
    }
);

watch(
    () => localValueLt.value,
    (newFilter) => {
        emit("change", localNameLt.value, newFilter);
    }
);

watch(
    () => valueGt.value,
    (newFilter) => {
        localValueGt.value = newFilter;
    }
);

watch(
    () => valueLt.value,
    (newFilter) => {
        localValueLt.value = newFilter;
    }
);
</script>

<template>
    <div>
        <small>Filter by {{ props.filter.placeholder }}:</small>

        <BInputGroup>
            <!---------------------------- GREATER THAN ---------------------------->
            <BFormInput
                :id="`${props.identifier}-advanced-filter-${localNameGt}`"
                v-model="localValueGt"
                v-b-tooltip.focus.v-danger="hasError(localNameGt)"
                size="sm"
                :state="hasError(localNameGt) ? false : null"
                :placeholder="localPlaceholder('gt')"
                :disabled="props.disabled"
                @keyup.enter="emit('on-enter')"
                @keyup.esc="emit('on-esc')" />

            <BInputGroupAppend v-if="isDateType">
                <BFormDatepicker v-model="localValueGt" reset-button button-only size="sm" :disabled="props.disabled" />
            </BInputGroupAppend>
            <!--------------------------------------------------------------------->

            <!---------------------------- LESSER THAN ---------------------------->
            <BFormInput
                :id="`${props.identifier}-advanced-filter-${localNameLt}`"
                v-model="localValueLt"
                v-b-tooltip.focus.v-danger="hasError(localNameLt)"
                size="sm"
                :state="hasError(localNameLt) ? false : null"
                :placeholder="localPlaceholder('lt')"
                :disabled="props.disabled"
                @keyup.enter="emit('on-enter')"
                @keyup.esc="emit('on-esc')" />

            <BInputGroupAppend v-if="isDateType">
                <BFormDatepicker v-model="localValueLt" reset-button button-only size="sm" :disabled="props.disabled" />
            </BInputGroupAppend>
            <!--------------------------------------------------------------------->
        </BInputGroup>
    </div>
</template>
