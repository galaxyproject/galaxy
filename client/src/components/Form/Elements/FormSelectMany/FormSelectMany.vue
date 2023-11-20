<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLongArrowAltLeft, faLongArrowAltRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { refDebounced } from "@vueuse/core";
import { BButton, BFormInput, BInputGroup } from "bootstrap-vue";
import { computed, nextTick, type PropType, reactive, ref } from "vue";

import { useUid } from "@/composables/utils/uid";

import { useHighlight } from "./useHighlight";
import { filterOptions } from "./worker/filterOptions";
import { useSelectMany } from "./worker/selectMany";

library.add(faLongArrowAltLeft, faLongArrowAltRight);

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
    optional: {
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
});

const emit = defineEmits<{
    (e: "input", value: Array<SelectValue>): void;
}>();

const searchValue = ref("");
const useRegex = ref(false);
const caseSensitive = ref(false);

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

const selected = computed({
    get() {
        return Array.isArray(props.value) ? props.value : [props.value];
    },
    set(value) {
        emit("input", value);
    },
});

const regexInvalid = computed(() => useRegex.value && searchRegex.value === null);
const asRegex = computed(() => searchRegex.value !== null);

const selectedDisplayCount = ref(500);
const unselectedDisplayCount = ref(500);

const { unselectedOptionsFiltered, selectedOptionsFiltered, running, moreUnselected, moreSelected } = useSelectMany({
    optionsArray: computed(() => props.options),
    filter: searchValue,
    selected,
    selectedDisplayCount,
    unselectedDisplayCount,
    asRegex,
    caseSensitive,
});

const workerRunning = refDebounced(running, 1000);

async function selectOption(index: number) {
    const [option] = unselectedOptionsFiltered.value.splice(index, 1);

    if (option) {
        selected.value.push(option.value);
    }

    // select the element which now is where the removed element just was
    // to improve keyboard navigation
    await nextTick();

    const el = document.getElementById(`${props.id}-unselected-${index}`);
    if (el) {
        el.focus();
    } else {
        document.getElementById(`${props.id}-unselected-${index - 1}`)?.focus();
    }
}

async function deselectOption(index: number) {
    const [option] = selectedOptionsFiltered.value.splice(index, 1);

    if (option) {
        const i = selected.value.indexOf(option.value);
        selected.value.splice(i, 1);
    }

    await nextTick();

    const el = document.getElementById(`${props.id}-selected-${index}`);
    if (el) {
        el.focus();
    } else {
        document.getElementById(`${props.id}-selected-${index - 1}`)?.focus();
    }
}

function selectAll() {
    if (highlightUnselected.highlightedIndexes.length > 0) {
        const highlightedValues = highlightUnselected.highlightedOptions.map((o) => o.value);
        const selectedSet = new Set([...selected.value, ...highlightedValues]);
        selected.value = Array.from(selectedSet);
    } else if (searchValue.value === "") {
        selected.value = props.options.map((o) => o.value);
    } else {
        const filteredValues = filterOptions(
            props.options,
            searchValue.value,
            asRegex.value,
            caseSensitive.value,
            searchRegex.value
        ).map((o) => o.value);

        const selectedSet = new Set([...selected.value, ...filteredValues]);
        selected.value = Array.from(selectedSet);
    }

    unselectedOptionsFiltered.value = [];
}

function deselectAll() {
    if (searchValue.value === "") {
        selected.value = [];
        //} else if (highlightedSelected.value.length > 0) {
        // todo
    } else {
        const selectedSet = new Set(selected.value);
        const filteredValues = filterOptions(
            props.options,
            searchValue.value,
            asRegex.value,
            caseSensitive.value,
            searchRegex.value
        ).map((o) => o.value);

        filteredValues.forEach((v) => selectedSet.delete(v));
        selected.value = Array.from(selectedSet);
    }

    selectedOptionsFiltered.value = [];
}

function optionOnKey(selected: "selected" | "unselected", event: KeyboardEvent, index: number) {
    if (!["ArrowUp", "ArrowDown"].includes(event.key)) {
        return;
    }

    event.preventDefault();

    const nextIndex = event.key === "ArrowUp" ? index - 1 : index + 1;
    document.getElementById(`${props.id}-${selected}-${nextIndex}`)?.focus();
}

const highlightUnselected = reactive(useHighlight(unselectedOptionsFiltered));

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
    /*if (highlightedSelected.value.length > 0) {
        return "Deselect highlighted";
    } else*/ if (searchValue.value === "") {
        return "Deselect all";
    } else {
        return "Deselect filtered";
    }
});
</script>

<template>
    <section :id="props.id" class="form-select-many">
        <BInputGroup>
            <BFormInput
                v-model="searchValue"
                :state="regexInvalid ? false : undefined"
                :debounce="300"
                :placeholder="props.placeholder"></BFormInput>

            <template v-slot:append>
                <BButton
                    class="toggle-button"
                    :variant="caseSensitive ? 'primary' : 'outline-primary'"
                    role="switch"
                    :aria-checked="caseSensitive"
                    title="case sensitive"
                    @click="caseSensitive = !caseSensitive">
                    Aa
                </BButton>
                <BButton
                    class="toggle-button"
                    :variant="useRegex ? 'primary' : 'outline-primary'"
                    role="switch"
                    :aria-checked="useRegex"
                    title="use regex"
                    @click="useRegex = !useRegex">
                    .*
                </BButton>
            </template>
        </BInputGroup>

        <div class="options-box border rounded mt-2">
            <div class="selection-heading border-right px-2">
                <span>Unselected</span>
                <BButton class="selection-button" :title="selectText" variant="primary" @click="selectAll">
                    {{ selectText }}
                    <FontAwesomeIcon icon="fa-long-arrow-alt-right" />
                </BButton>
            </div>

            <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
            <div
                class="options-list unselected border-right"
                tabindex="-1"
                @keydown.up.down.prevent
                @keyup.shift="highlightUnselected.abortHighlight()">
                <button
                    v-for="(option, i) in unselectedOptionsFiltered"
                    :id="`${props.id}-unselected-${i}`"
                    :key="option.label"
                    :tabindex="i === 0 ? 0 : -1"
                    :class="{ highlighted: highlightUnselected.highlightedIndexes.includes(i) }"
                    @click.shift.exact="highlightUnselected.onRangeHighlight(i)"
                    @click.shift.ctrl.exact="highlightUnselected.onRangeRemoveHighlight(i)"
                    @click.ctrl.exact="highlightUnselected.toggleHighlight(i)"
                    @click.exact="selectOption(i)"
                    @keydown="(e) => optionOnKey('unselected', e, i)">
                    {{ option.label }}
                </button>

                <span v-if="moreUnselected" class="show-more-indicator">
                    Limited to {{ unselectedDisplayCount }} options.
                    <button @click="unselectedDisplayCount += 500">Show more</button>
                </span>
            </div>
            <div class="selection-heading px-2">
                <span>Selected</span>
                <BButton class="selection-button" :title="deselectText" variant="primary" @click="deselectAll">
                    <FontAwesomeIcon icon="fa-long-arrow-alt-left" />
                    {{ deselectText }}
                </BButton>
            </div>
            <div class="options-list selected" tabindex="-1" @keydown.up.down.prevent>
                <button
                    v-for="(option, i) in selectedOptionsFiltered"
                    :id="`${props.id}-selected-${i}`"
                    :key="option.label"
                    :tabindex="i === 0 ? 0 : -1"
                    @click="deselectOption(i)"
                    @keydown="(e) => optionOnKey('selected', e, i)">
                    {{ option.label }}
                </button>

                <span v-if="moreSelected" class="show-more-indicator">
                    Limited to {{ selectedDisplayCount }} options.
                    <button @click="selectedDisplayCount += 500">Show more</button>
                </span>
            </div>
        </div>
        <div class="bottom-row-info">
            <span> Shift to highlight range. Ctrl to highlight multiple </span>
            <span v-if="workerRunning"> Processing... </span>
        </div>
    </section>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.form-select-many {
    .toggle-button {
        padding-left: 0;
        padding-right: 0;
        width: 2rem;
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
        }
    }
}

.options-list {
    overflow: scroll;
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

        button::after {
            content: none;
        }

        button {
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
}
</style>
