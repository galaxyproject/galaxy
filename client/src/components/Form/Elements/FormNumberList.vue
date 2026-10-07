<script setup lang="ts">
import { faPlus, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, watch } from "vue";

import FormNumber from "./FormNumber.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

type NumberValue = number | string;

interface Row {
    key: number;
    value: NumberValue;
}

const props = withDefaults(
    defineProps<{
        id?: string;
        value?: NumberValue | NumberValue[] | null;
        type: "integer" | "float";
        min?: number | null;
        max?: number | null;
        placeholder?: string;
        optional?: boolean;
        showState?: boolean;
    }>(),
    {
        id: "",
        value: null,
        min: undefined,
        max: undefined,
        placeholder: "",
        optional: false,
        showState: false,
    },
);

const emit = defineEmits<{
    (e: "input", value: number[] | null): void;
}>();

let nextKey = 0;

function toValues(value: NumberValue | NumberValue[] | null | undefined): NumberValue[] {
    if (value === null || value === undefined || value === "") {
        return [];
    }
    if (Array.isArray(value)) {
        return value;
    }
    if (typeof value === "string") {
        return value
            .split(/[\n,]/)
            .map((v) => v.trim())
            .filter((v) => v !== "");
    }
    return [value];
}

function toRows(values: NumberValue[]): Row[] {
    const valueRows = values.length ? values : [""];
    return valueRows.map((value) => ({ key: nextKey++, value }));
}

function toNumbers(values: NumberValue[]): number[] {
    return values.filter((v) => v !== "" && v !== null && v !== undefined).map((v) => Number(v));
}

const rows = ref<Row[]>(toRows(toValues(props.value)));

function emitValue() {
    const numbers = toNumbers(rows.value.map((row) => row.value));
    emit("input", numbers.length ? numbers : null);
}

function onRowInput(index: number, value: NumberValue) {
    rows.value[index]!.value = value;
    emitValue();
}

function addRow() {
    rows.value.push({ key: nextKey++, value: "" });
}

function removeRow(index: number) {
    rows.value.splice(index, 1);
    emitValue();
}

watch(
    () => props.value,
    (newValue) => {
        const incoming = toNumbers(toValues(newValue));
        const current = toNumbers(rows.value.map((row) => row.value));
        if (JSON.stringify(incoming) !== JSON.stringify(current)) {
            rows.value = toRows(incoming);
        }
    },
);
</script>

<template>
    <div :id="props.id">
        <div
            v-for="(row, index) in rows"
            :key="row.key"
            class="d-flex align-items-start mb-1"
            data-description="number list row">
            <FormNumber
                class="flex-grow-1"
                :value="row.value"
                :type="props.type"
                :min="props.min ?? undefined"
                :max="props.max ?? undefined"
                :placeholder="props.placeholder"
                :optional="props.optional"
                :show-state="props.showState"
                @input="onRowInput(index, $event)" />
            <GButton
                class="ml-1"
                tooltip
                title="Remove value"
                color="blue"
                transparent
                size="small"
                :disabled="rows.length === 1"
                data-description="remove value"
                @click="removeRow(index)">
                <FontAwesomeIcon :icon="faTimes" />
            </GButton>
        </div>
        <GButton size="small" data-description="add value" @click="addRow">
            <FontAwesomeIcon :icon="faPlus" class="mr-1" />
            Add value
        </GButton>
    </div>
</template>
