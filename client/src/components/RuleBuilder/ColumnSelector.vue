<script setup lang="ts">
import { computed } from "vue";

import localize from "@/utils/localization";

import SelectBasic from "@/components/RuleBuilder/SelectBasic.vue";

interface Props {
    /** Column headers to choose from */
    colHeaders: string[];
    /** Selected column index, or indices when multiple or valueAsList is set */
    target: number | number[];
    /**
     * Help text shown as the label's title
     * @default undefined
     */
    help?: string;
    /**
     * Label shown next to the selector
     * @default "From Column"
     */
    label?: string;
    /**
     * Allow selecting more than one column
     * @default false
     */
    multiple?: boolean;
    /**
     * Show multiple selections as an ordered, editable list
     * @default false
     */
    ordered?: boolean;
    /**
     * Whether the ordered list shows the add-column selector
     * @default false
     */
    orderedEdit?: boolean;
    /**
     * Emit a single selection as a one-element list
     * @default false
     */
    valueAsList?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    help: undefined,
    label: localize("From Column"),
    multiple: false,
    ordered: false,
    orderedEdit: false,
    valueAsList: false,
});

const emit = defineEmits<{
    (e: "update:target", value: number | number[]): void;
    (e: "update:orderedEdit", value: boolean): void;
}>();

const title = localize("Select a column");

const targetList = computed(() => (Array.isArray(props.target) ? props.target : [props.target]));

const columnOptions = computed(() => props.colHeaders.map((col, index) => ({ id: index, text: col })));

const remainingOptions = computed(() => {
    if (!props.multiple) {
        return columnOptions.value;
    }
    const exclude = new Set(targetList.value.map(Number));
    return columnOptions.value.filter((opt) => !exclude.has(opt.id));
});

// SelectBasic emits the selected option id(s), or null when cleared.
function handleInput(value: number | number[] | null) {
    if (props.multiple) {
        // https://stackoverflow.com/questions/262427/why-does-parseint-yield-nan-with-arraymap
        const val = (value as number[]).map((idx) => parseInt(String(idx)));
        emit("update:target", val);
    } else {
        const val = parseInt(String(value));
        emit("update:target", props.valueAsList ? [val] : val);
    }
}

// Emit new arrays instead of mutating the target prop.
function handleAdd(value: number | null) {
    emit("update:target", [...targetList.value, parseInt(String(value))]);
    emit("update:orderedEdit", false);
}

function handleRemove(index: number) {
    emit(
        "update:target",
        targetList.value.filter((_, i) => i !== index),
    );
}

// Swaps the column at index with the one above it.
function moveUp(index: number) {
    const reordered = [...targetList.value];
    const [moved] = reordered.splice(index, 1);
    if (moved !== undefined) {
        reordered.splice(index - 1, 0, moved);
    }
    emit("update:target", reordered);
}
</script>

<template>
    <div v-if="!multiple || !ordered" class="rule-column-selector">
        <div class="d-flex justify-content-end align-items-center">
            <span v-g-tooltip.hover class="mr-auto help-text" :title="help">{{ label }}</span>
            <div v-g-tooltip.hover class="mr-1" :title="title">
                <SelectBasic :value="target" :multiple="multiple" :options="columnOptions" @input="handleInput" />
            </div>
            <slot />
        </div>
    </div>
    <div v-else class="rule-column-selector">
        <span class="help-text" :title="help">{{ label }}</span>
        <slot />
        <ol>
            <li
                v-for="(targetEl, index) in targetList"
                :key="targetEl"
                :index="index"
                class="rule-column-selector-target">
                {{ colHeaders[targetEl] }}
                <span class="fa fa-times rule-column-selector-target-remove" @click="handleRemove(index)"></span>
                <span v-if="index !== 0" class="fa fa-arrow-up rule-column-selector-up" @click="moveUp(index)"></span>
                <span
                    v-if="index < targetList.length - 1"
                    class="fa fa-arrow-down rule-column-selector-down"
                    @click="moveUp(index + 1)"></span>
            </li>
            <li v-if="targetList.length < colHeaders.length">
                <span v-if="!orderedEdit" class="rule-column-selector-target-add">
                    <i @click="emit('update:orderedEdit', true)">... {{ localize("Assign Another Column") }}</i>
                </span>
                <span v-else class="rule-column-selector-target-select">
                    <SelectBasic placeholder="Select a column" :options="remainingOptions" @input="handleAdd" />
                </span>
            </li>
        </ol>
    </div>
</template>

<style scoped src="@/components/Help/help-text.scss" />
