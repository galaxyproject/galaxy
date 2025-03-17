<script setup lang="ts">
import { faLongArrowAltLeft, faLongArrowAltRight, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { refDebounced } from "@vueuse/core";
import { BButton, BFormInput } from "bootstrap-vue";
import { computed, nextTick, type PropType, reactive, ref, type UnwrapRef } from "vue";

import { useUid } from "@/composables/utils/uid";

import { useHighlight } from "./useHighlight";
import { filterOptions } from "./worker/filterOptions";
import { useSelectMany } from "./worker/selectMany";

type SelectValue = Record<string, unknown> | string | number | null;

interface SelectOption {
    label: string;
    value: SelectValue;
}

const props = defineProps({
    id: { type: String, default: () => useUid("form-select-many-").value },
    disabled: {
        type: Boolean,
        default: false,
    },
    options: {
        type: Array as PropType<Array<SelectOption>>,
        required: true,
    },
    placeholder: {
        type: String,
        default: "Search for options",
    },
    value: {
        type: Array as PropType<SelectValue | SelectValue[]>,
        default: null,
    },
    maintainSelectionOrder: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits<{
    (e: "input", value: Array<SelectValue>): void;
}>();

const searchValue = ref("");
const useRegex = ref(false);
const caseSensitive = ref(false);
const localSelectionOrder = computed(() => props.maintainSelectionOrder);

const searchRegex = computed(() => {
    if (useRegex.value) {
        try {
            const regex = new RegExp(searchValue.value, caseSensitive.value ? undefined : "i");
            return regex;
        } catch (e) {
            return null;
        }
    } else {
        return null;
    }
});

/** Wraps value prop so it can be set, and always returns an array */
const selected = computed({
    get() {
        if (props.value === null) {
            return [];
        } else if (Array.isArray(props.value)) {
            return props.value;
        } else {
            return [props.value];
        }
    },
    set(value) {
        emit("input", value);
    },
});

const regexInvalid = computed(() => useRegex.value && searchRegex.value === null);

// Limits amount of displayed options
const selectedDisplayCount = ref(1000);
const unselectedDisplayCount = ref(1000);

const filter = computed(() => searchRegex.value ?? searchValue.value);

// binding to worker thread
const { unselectedOptionsFiltered, selectedOptionsFiltered, running, moreUnselected, moreSelected } = useSelectMany({
    optionsArray: computed(() => props.options),
    filter,
    selected,
    selectedDisplayCount,
    unselectedDisplayCount,
    caseSensitive,
    maintainSelectionOrder: localSelectionOrder,
});

// debounced to it doesn't blink, and only appears when relevant
const workerRunning = refDebounced(running, 400);

/** generic event handler to handle highlighting of options */
function handleHighlight(
    event: MouseEvent | KeyboardEvent,
    index: number,
    highlightHandler: UnwrapRef<ReturnType<typeof useHighlight>>
) {
    if (event.shiftKey && event.ctrlKey) {
        highlightHandler.rangeRemoveHighlight(index);
    } else if (event.shiftKey) {
        highlightHandler.rangeHighlight(index);
    } else if (event.ctrlKey) {
        highlightHandler.toggleHighlight(index);
    }
}

/** focus option at given index, or previous option if that doesn't exist */
function focusOptionAtIndex(selected: "selected" | "unselected", index: number) {
    const el = document.getElementById(`${props.id}-${selected}-${index}`);
    if (el) {
        el.focus();
    } else {
        document.getElementById(`${props.id}-${selected}-${index - 1}`)?.focus();
    }
}

/** convert array of select options to a map of select labels to select values */
function optionsToLabelMap(options: SelectOption[]): Map<string, SelectValue> {
    return new Map(options.map((o) => [o.label, o.value]));
}

function valuesToOptions(values: SelectValue[]): SelectOption[] {
    function stringifyObject(value: SelectValue) {
        return typeof value === "object" && value !== null ? JSON.stringify(value) : value;
    }

    const comparableValues = values.map(stringifyObject);
    const valueSet = new Set(comparableValues);
    const options: SelectOption[] = [];

    props.options.forEach((option) => {
        if (valueSet.has(stringifyObject(option.value))) {
            options.push(option);
        }
    });

    return options;
}

async function selectOption(event: MouseEvent, index: number): Promise<void> {
    if (event.shiftKey || event.ctrlKey) {
        handleHighlight(event, index, highlightUnselected);
    } else {
        const [option] = unselectedOptionsFiltered.value.splice(index, 1);

        if (option) {
            selected.value = [...selected.value, option.value];
        }

        // select the element which now is where the removed element just was
        // to improve keyboard navigation
        await nextTick();
        focusOptionAtIndex("unselected", index);
    }
}

async function deselectOption(event: MouseEvent, index: number) {
    if (event.shiftKey || event.ctrlKey) {
        handleHighlight(event, index, highlightSelected);
    } else {
        const [option] = selectedOptionsFiltered.value.splice(index, 1);

        if (option) {
            const i = selected.value.findIndex((selectedValue) => {
                if (typeof selectedValue === "string") {
                    return selectedValue === option.value;
                } else if (typeof selectedValue === "object" && typeof option.value === "object") {
                    // in case values are objects, compare their ids (if they have the 'id' property)
                    return selectedValue?.id === option.value?.id;
                }
                return false;
            });
            selected.value = selected.value.flatMap((value, index) => (index === i ? [] : [value]));
        }

        await nextTick();
        focusOptionAtIndex("selected", index);
    }
}

function selectAll() {
    if (highlightUnselected.highlightedIndexes.length > 0) {
        const highlightedValues = highlightUnselected.highlightedOptions.map((o) => o.value);
        selected.value = [...selected.value, ...highlightedValues];

        const highlightedMap = optionsToLabelMap(highlightUnselected.highlightedOptions);
        unselectedOptionsFiltered.value.filter((o) => highlightedMap.has(o.label));
    } else if (searchValue.value === "") {
        selected.value = props.options.map((o) => o.value);

        unselectedOptionsFiltered.value = [];
    } else {
        const filteredValues = filterOptions(props.options, filter.value, caseSensitive.value).map((o) => o.value);

        const selectedSet = new Set([...selected.value, ...filteredValues]);
        selected.value = Array.from(selectedSet);

        unselectedOptionsFiltered.value = [];
    }
}

function deselectAll() {
    if (highlightSelected.highlightedIndexes.length > 0) {
        const selectedMap = optionsToLabelMap(valuesToOptions(selected.value));
        const highlightedMap = optionsToLabelMap(highlightSelected.highlightedOptions);

        highlightedMap.forEach((_value, label) => selectedMap.delete(label));
        selected.value = Array.from(selectedMap.values());

        selectedOptionsFiltered.value.filter((o) => highlightedMap.has(o.label));
    } else if (searchValue.value === "") {
        selected.value = [];
        selectedOptionsFiltered.value = [];
    } else {
        const selectedSet = new Set(selected.value);
        const filteredValues = filterOptions(props.options, filter.value, caseSensitive.value).map((o) => o.value);

        filteredValues.forEach((v) => selectedSet.delete(v));
        selected.value = Array.from(selectedSet);

        selectedOptionsFiltered.value = [];
    }
}

function optionOnKey(selected: "selected" | "unselected", event: KeyboardEvent, index: number) {
    // handle highlighting
    if ([" ", "Enter"].includes(event.key) && (event.shiftKey || event.ctrlKey)) {
        const highlightHandler = selected === "selected" ? highlightSelected : highlightUnselected;
        handleHighlight(event, index, highlightHandler);
        event.preventDefault();
        return;
    }

    if (!["ArrowUp", "ArrowDown"].includes(event.key)) {
        return;
    }

    event.preventDefault();

    // handle arrow navigation
    const nextIndex = event.key === "ArrowUp" ? index - 1 : index + 1;
    document.getElementById(`${props.id}-${selected}-${nextIndex}`)?.focus();
}

const highlightUnselected = reactive(useHighlight(unselectedOptionsFiltered));
const highlightSelected = reactive(useHighlight(selectedOptionsFiltered));

const selectText = computed(() => {
    if (highlightUnselected.highlightedIndexes.length > 0) {
        return "Select highlighted";
    } else if (searchValue.value === "") {
        return "Select all";
    } else {
        return "Select filtered";
    }
});

const deselectText = computed(() => {
    if (highlightSelected.highlightedIndexes.length > 0) {
        return "Deselect highlighted";
    } else if (searchValue.value === "") {
        return "Deselect all";
    } else {
        return "Deselect filtered";
    }
});

const unselectedCount = computed(() => {
    if (searchValue.value === "") {
        return `${props.options.length - selected.value.length}`;
    } else {
        let countString = `${unselectedOptionsFiltered.value.length}`;
        if (moreUnselected.value) {
            countString += "+";
        }
        return countString;
    }
});

const selectedCount = computed(() => {
    if (searchValue.value === "") {
        return `${selected.value.length}`;
    } else {
        let countString = `${selectedOptionsFiltered.value.length}`;
        if (moreSelected.value) {
            countString += "+";
        }
        return countString;
    }
});
</script>

<template>
    <div :id="props.id" class="form-select-many">
        <fieldset class="search-bar">
            <fieldset class="search-input">
                <BFormInput
                    v-model="searchValue"
                    type="search"
                    :state="regexInvalid ? false : undefined"
                    :debounce="300"
                    :placeholder="props.placeholder" />
                <button
                    class="inline-icon-button"
                    :class="{ hidden: searchValue === '' }"
                    title="Clear search"
                    @click="searchValue = ''">
                    <FontAwesomeIcon :icon="faTimes" />
                </button>
            </fieldset>

            <BButton
                class="toggle-button case-sensitivity"
                :variant="caseSensitive ? 'primary' : 'outline-primary'"
                role="switch"
                :aria-checked="`${caseSensitive}`"
                title="case sensitive"
                @click="caseSensitive = !caseSensitive">
                Aa
            </BButton>
            <BButton
                class="toggle-button use-regex"
                :variant="useRegex ? 'primary' : 'outline-primary'"
                role="switch"
                :aria-checked="`${useRegex}`"
                title="use regex"
                @click="useRegex = !useRegex">
                .*
            </BButton>
        </fieldset>

        <div class="options-box border rounded mt-2">
            <div class="selection-heading border-right px-2">
                <span>
                    Unselected
                    <span class="font-weight-normal unselected-count"> ({{ unselectedCount }}) </span>
                </span>
                <BButton class="selection-button select" :title="selectText" variant="primary" @click="selectAll">
                    {{ selectText }}
                    <FontAwesomeIcon :icon="faLongArrowAltRight" />
                </BButton>
            </div>

            <div
                class="options-list unselected border-right"
                tabindex="-1"
                @keydown.up.down.prevent
                @blur="highlightUnselected.abortHighlight">
                <button
                    v-for="(option, i) in unselectedOptionsFiltered"
                    :id="`${props.id}-unselected-${i}`"
                    :key="option.label"
                    :tabindex="i === 0 ? 0 : -1"
                    :class="{ highlighted: highlightUnselected.highlightedIndexes.includes(i) }"
                    @click="(e) => selectOption(e, i)"
                    @keydown="(e) => optionOnKey('unselected', e, i)">
                    <slot name="label-area" v-bind="option">
                        {{ option.label }}
                    </slot>
                </button>

                <span v-if="moreUnselected" class="show-more-indicator">
                    Limited to {{ unselectedDisplayCount }} options.
                    <button class="show-more-button" @click="unselectedDisplayCount += 500">Show more</button>
                </span>
            </div>
            <div class="selection-heading px-2">
                <span>
                    Selected
                    <span class="font-weight-normal selected-count"> ({{ selectedCount }}) </span>
                </span>
                <BButton class="selection-button deselect" :title="deselectText" variant="primary" @click="deselectAll">
                    <FontAwesomeIcon :icon="faLongArrowAltLeft" />
                    {{ deselectText }}
                </BButton>
            </div>

            <div
                class="options-list selected"
                tabindex="-1"
                @keydown.up.down.prevent
                @blur="highlightSelected.abortHighlight">
                <button
                    v-for="(option, i) in selectedOptionsFiltered"
                    :id="`${props.id}-selected-${i}`"
                    :key="option.label"
                    :tabindex="i === 0 ? 0 : -1"
                    :class="{ highlighted: highlightSelected.highlightedIndexes.includes(i) }"
                    @click="(e) => deselectOption(e, i)"
                    @keydown="(e) => optionOnKey('selected', e, i)">
                    <slot name="label-area" v-bind="option">
                        {{ option.label }}
                    </slot>
                </button>

                <span v-if="moreSelected" class="show-more-indicator">
                    Limited to {{ selectedDisplayCount }} options.
                    <button class="show-more-button" @click="selectedDisplayCount += 500">Show more</button>
                </span>
            </div>
        </div>
        <div class="bottom-row-info">
            <span> Shift to highlight range. Ctrl to highlight multiple </span>
            <span v-if="workerRunning" class="working-indicator"> Processing... </span>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.form-select-many {
    .search-bar {
        display: grid;
        grid-template-columns: 1fr 2.125rem 2.125rem;

        > *:not(:first-child):not(:last-child) {
            border-radius: 0;
        }

        > *:last-child {
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
        }

        .search-input {
            position: relative;

            input {
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
            }

            button {
                position: absolute;
                right: 4px;
                top: 4px;
                height: calc(100% - 8px);
                width: 26px;

                &.hidden:not(:focus) {
                    color: transparent;

                    &:hover {
                        color: $white;
                    }
                }
            }
        }
    }

    .toggle-button {
        padding-left: 0;
        padding-right: 0;
    }
}

.options-box {
    resize: vertical;
    overflow: hidden;
    min-height: 200px;
    height: 200px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto 1fr;
    grid-auto-flow: column;
    padding: 0.5rem;

    .selection-heading {
        color: $gray-600;
        font-weight: bold;
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;

        .selection-button {
            height: 20px;
            padding: 0 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }
    }
}

.options-list {
    overflow-y: scroll;
    display: flex;
    flex-direction: column;

    button {
        text-align: start;
        border: none;
        padding: 0 0.5rem;
        background: none;
        transition: none;
        display: flex;
        justify-content: space-between;

        &.highlighted {
            background-color: $brand-info;
            border-radius: 0;
            color: $white;

            &:hover,
            &:focus {
                background-color: $brand-primary;

                &::after {
                    color: $white;
                }
            }
        }

        &:focus-visible {
            outline-color: $brand-primary;
            outline-width: 2px;
            outline-offset: -2px;
            outline-style: solid;
            box-shadow: none;
        }

        &:hover,
        &:focus {
            background-color: $brand-secondary;

            &::after {
                content: "click to select";
                color: darken($brand-secondary, 40%);
                font-weight: bold;
            }
        }

        &:focus-visible::after {
            content: "enter to select";
        }
    }

    .show-more-indicator {
        display: flex;
        font-style: italic;
        padding-left: 0.5rem;
        color: darken($gray-400, 20%);

        .show-more-button:hover::after,
        .show-more-button:focus::after {
            content: none;
        }

        .show-more-button {
            color: $brand-info;
            text-decoration: underline;
        }
    }
}

.options-list.selected {
    button {
        &:hover,
        &:focus {
            &::after {
                content: "click to deselect";
            }
        }

        &:focus-visible::after {
            content: "enter to deselect";
        }
    }
}

.bottom-row-info {
    font-style: italic;
    color: darken($gray-400, 10%);
    font-size: 0.75rem;
    padding: 0 0.25rem;
    width: 100%;
    display: flex;
    justify-content: space-between;

    .working-indicator {
        color: $brand-primary;
    }
}
</style>
