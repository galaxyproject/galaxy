<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLongArrowAltLeft, faLongArrowAltRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormInput, BInputGroup } from "bootstrap-vue";
import { computed, type PropType, ref } from "vue";

import { useUid } from "@/composables/utils/uid";

import { filterOptions } from "./worker/filterOptions";
import { useSelectMany } from "./worker/selectMany";

library.add(faLongArrowAltLeft, faLongArrowAltRight);

type SelectValue = Record<string, unknown> | string | number | null;

interface SelectOption {
    label: string;
    value: SelectValue;
}

const props = defineProps({
    id: { type: String, default: useUid("form-select-many-").value },
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

const { unselectedOptionsFiltered, selectedOptionsFiltered } = useSelectMany({
    optionsArray: computed(() => props.options),
    filter: searchValue,
    selected,
    selectedDisplayCount: ref(1000),
    unselectedDisplayCount: ref(1000),
    asRegex,
    caseSensitive,
});

function selectOption(index: number) {
    const [option] = unselectedOptionsFiltered.value.splice(index, 1);

    if (option) {
        selected.value.push(option.value);
    }
}

function deselectOption(index: number) {
    const [option] = selectedOptionsFiltered.value.splice(index, 1);

    if (option) {
        const i = selected.value.indexOf(option.value);
        selected.value.splice(i, 1);
    }
}

function selectAll() {
    if (searchValue.value === "") {
        selected.value = props.options.map((o) => o.value);
    } else if (highlightedUnselected.value.length > 0) {
        // todo
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
    } else if (highlightedSelected.value.length > 0) {
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
    document.getElementById(`select-many-${props.id}-${selected}-${nextIndex}`)?.focus();
}

const highlightedUnselected = ref([]);
const highlightedSelected = ref([]);

const selectText = computed(() => {
    if (highlightedUnselected.value.length > 0) {
        return "Select highlighted";
    } else if (searchValue.value === "") {
        return "Select all";
    } else {
        return "Select filtered";
    }
});

const deselectText = computed(() => {
    if (highlightedSelected.value.length > 0) {
        return "Deselect highlighted";
    } else if (searchValue.value === "") {
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

        <div class="options-box border rounded p-2 mt-2">
            <div class="selection-heading border-right px-2">
                <span>Unselected</span>
                <BButton class="selection-button" :title="selectText" variant="primary" @click="selectAll">
                    {{ selectText }}
                    <FontAwesomeIcon icon="fa-long-arrow-alt-right" />
                </BButton>
            </div>
            <div class="options-list unselected border-right" tabindex="-1" @keydown.up.down.prevent>
                <button
                    v-for="(option, i) in unselectedOptionsFiltered"
                    :id="`select-many-${props.id}-unselected-${i}`"
                    :key="option.label"
                    :tabindex="i === 0 ? 0 : -1"
                    @click="selectOption(i)"
                    @keyup="(e) => optionOnKey('unselected', e, i)">
                    {{ option.label }}
                </button>
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
                    :id="`select-many-${props.id}-selected-${i}`"
                    :key="option.label"
                    :tabindex="i === 0 ? 0 : -1"
                    @click="deselectOption(i)"
                    @keyup="(e) => optionOnKey('selected', e, i)">
                    {{ option.label }}
                </button>
            </div>
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

        &:hover {
            background-color: $brand-secondary;
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
            &::after {
                content: "click to select";
                color: darken($brand-secondary, 40%);
                font-weight: bold;
            }
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
    }
}
</style>
