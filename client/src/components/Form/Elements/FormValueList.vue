<script setup lang="ts">
import { faPlus, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import FormNumber from "./FormNumber.vue";
import FormText from "./FormText.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

type FieldValue = number | string;

interface DatalistItem {
    label: string;
    value: string;
}

interface Row {
    key: number;
    value: FieldValue;
}

const props = withDefaults(
    defineProps<{
        id?: string;
        value?: FieldValue | FieldValue[] | null;
        type: "integer" | "float" | "text";
        min?: number | null;
        max?: number | null;
        placeholder?: string;
        optional?: boolean;
        showState?: boolean;
        datalist?: DatalistItem[];
    }>(),
    {
        id: "",
        value: null,
        min: undefined,
        max: undefined,
        placeholder: "",
        optional: false,
        showState: false,
        datalist: undefined,
    },
);

const emit = defineEmits<{
    (e: "input", value: FieldValue[] | null): void;
}>();

const isText = computed(() => props.type === "text");

let nextKey = 0;

function toValues(value: FieldValue | FieldValue[] | null | undefined): FieldValue[] {
    if (value === null || value === undefined || value === "") {
        return [];
    }
    if (Array.isArray(value)) {
        return value;
    }
    if (typeof value === "string" && !isText.value) {
        return value
            .split(/[\n,]/)
            .map((v) => v.trim())
            .filter((v) => v !== "");
    }
    return [value];
}

function toRows(values: FieldValue[]): Row[] {
    const valueRows = values.length ? values : [""];
    return valueRows.map((value) => ({ key: nextKey++, value }));
}

function toEmitted(values: FieldValue[]): FieldValue[] {
    const entered = values.filter((v) => v !== "" && v !== null && v !== undefined);
    return isText.value ? entered.map((v) => String(v)) : entered.map((v) => Number(v));
}

const rows = ref<Row[]>(toRows(toValues(props.value)));

function emitValue() {
    const values = toEmitted(rows.value.map((row) => row.value));
    emit("input", values.length ? values : null);
}

function onRowInput(index: number, value: FieldValue) {
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
        const incoming = toEmitted(toValues(newValue));
        const current = toEmitted(rows.value.map((row) => row.value));
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
            data-description="value list row">
            <FormText
                v-if="isText"
                :id="`${props.id}-${row.key}`"
                class="flex-grow-1"
                :value="String(row.value)"
                :placeholder="props.placeholder"
                :optional="props.optional"
                :show-state="props.showState"
                :datalist="props.datalist"
                @input="onRowInput(index, $event)" />
            <FormNumber
                v-else
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
