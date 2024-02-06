<script setup lang="ts">
/**
 * This component does not control it's own open/closed state!
 * It expects it's parent component to do so.
 * It is a building block for building a custom Multiselect,
 * not a fully featured Multiselect alternative
 */

import { library } from "@fortawesome/fontawesome-svg-core";
import { faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useElementBounding } from "@vueuse/core";
import { computed, nextTick, onMounted, ref, watch } from "vue";
// @ts-ignore missing types
import Vue2Teleport from "vue2-teleport";

import { useUid } from "@/composables/utils/uid";

library.add(faChevronUp);

const props = withDefaults(
    defineProps<{
        options: Array<string>;
        selected: Array<string>;
        maxShownOptions?: number;
        placeholder?: string;
        id?: string;
        validator?: (option: string) => boolean;
    }>(),
    {
        maxShownOptions: 50,
        placeholder: "type to search",
        id: () => useUid("headless-multiselect-").value,
        validator: () => () => true,
    }
);

const emit = defineEmits<{
    (e: "close"): void;
    (e: "input", selected: string[]): void;
    (e: "addOption", newOption: string): void;
}>();

const inputField = ref<HTMLInputElement | null>(null);

onMounted(async () => {
    await nextTick();
    inputField.value?.focus();
});

const searchValue = ref("");
const trimmedSearchValue = computed(() => searchValue.value.trim());
const optionsAsSet = computed(() => new Set(props.options));
const searchValueEmpty = computed(() => trimmedSearchValue.value === "");
const searchValueInOptions = computed(() => optionsAsSet.value.has(trimmedSearchValue.value));
const searchValueValid = computed(() => searchValueEmpty.value || props.validator(trimmedSearchValue.value));

const filteredOptions = computed(() => {
    if (searchValueEmpty.value) {
        return props.options;
    } else {
        return props.options.filter((option) => option.includes(trimmedSearchValue.value));
    }
});

const trimmedOptions = computed(() => {
    if (searchValueEmpty.value || searchValueInOptions.value) {
        return filteredOptions.value.slice(0, props.maxShownOptions);
    } else {
        const trimmed = filteredOptions.value.slice(0, props.maxShownOptions - 1);
        trimmed.unshift(trimmedSearchValue.value);
        return trimmed;
    }
});

const highlightedOption = ref(0);

watch(
    () => trimmedSearchValue.value,
    () => {
        highlightedOption.value = 0;
    }
);

function onOptionHover(index: number) {
    highlightedOption.value = index;
}

function onInputUp() {
    if (highlightedOption.value > 0) {
        highlightedOption.value -= 1;
    }

    getOptionWithId(highlightedOption.value)?.scrollIntoView({ block: "center" });
}

function onInputDown() {
    if (highlightedOption.value < trimmedOptions.value.length) {
        highlightedOption.value += 1;
    }

    getOptionWithId(highlightedOption.value)?.scrollIntoView({ block: "center" });
}

function getOptionWithId(id: number) {
    return document.querySelector(`#${props.id}-option-${id}`) as HTMLButtonElement | null;
}

function onOptionSelected(option: string) {
    if (!optionsAsSet.value.has(option)) {
        emit("addOption", option);
        return;
    }

    const set = new Set(props.selected);

    if (set.has(option)) {
        set.delete(option);
    } else {
        set.add(option);
    }

    emit("input", Array.from(set));
}

function onInputEnter() {
    const option = trimmedOptions.value[highlightedOption.value];

    if (option) {
        onOptionSelected(option);
        searchValue.value = "";
    }
}

// allow for keyboard navigation
function onOptionKey(event: KeyboardEvent, index: number) {
    if (event.key === "ArrowUp") {
        if (index < 1) {
            inputField.value?.focus();
        } else {
            getOptionWithId(index - 1)?.focus();
        }
    } else if (event.key === "ArrowDown") {
        getOptionWithId(index + 1)?.focus();
    }
}

function onBlur(e: FocusEvent) {
    const newTarget = e.relatedTarget;

    if (!(newTarget instanceof HTMLElement)) {
        emit("close");
    } else if (newTarget.getAttribute("data-parent-id") !== props.id) {
        emit("close");
    }
}

// emulate tab behavior, because options list is teleported to the app layer
function onCloseButtonTab(event: KeyboardEvent) {
    if (!event.shiftKey) {
        getOptionWithId(0)?.focus();
        event.preventDefault();
    }
}

const closeButton = ref<HTMLButtonElement | null>(null);

function getNextFocusableElement() {
    if (!closeButton.value) {
        return;
    }

    const focusableElementSelector =
        "a:not([disabled]), button:not([disabled]), input[type=text]:not([disabled]), [tabindex]:not([disabled]):not([tabindex='-1'])";
    const focusableElements = document.querySelectorAll(focusableElementSelector);
    const closeButtonIndex = Array.from(focusableElements).indexOf(closeButton.value);
    return focusableElements.item(closeButtonIndex + 1) as HTMLElement | null;
}

// since our popup is teleported to the app layer, we need to emulate
// tab behavior at the start and end of the list.
function onOptionTab(event: KeyboardEvent, index: number) {
    if (index === 0 && event.shiftKey) {
        closeButton.value?.focus();
        event.preventDefault();
    } else if (index === trimmedOptions.value.length - 1) {
        getNextFocusableElement()?.focus();
        event.preventDefault();
    }
}

const root = ref<HTMLDivElement | null>(null);
const bounds = useElementBounding(root);
</script>

<template>
    <div ref="root" class="headless-multiselect" @blur.capture="onBlur">
        <fieldset>
            <input
                :id="`${props.id}-input`"
                ref="inputField"
                v-model="searchValue"
                aria-autocomplete="list"
                :aria-label="props.placeholder"
                role="searchbox"
                aria-haspopup="listbox"
                type="text"
                :aria-invalid="props.validator(trimmedSearchValue)"
                :aria-owns="`${props.id}-options`"
                :aria-activedescendant="`${props.id}-options`"
                :data-parent-id="props.id"
                :placeholder="props.placeholder"
                @keydown.up="onInputUp"
                @keydown.down="onInputDown"
                @keydown.enter="onInputEnter" />
            <button
                ref="closeButton"
                :data-parent-id="props.id"
                title="close"
                @click="emit('close')"
                @keydown.tab="onCloseButtonTab">
                <FontAwesomeIcon icon="fa-chevron-up" />
            </button>
        </fieldset>

        <Vue2Teleport to="#app">
            <div
                :id="`${props.id}-options`"
                aria-expanded="true"
                role="listbox"
                class="headless-multiselect__options"
                :style="{
                    '--top': `${bounds.top.value}px`,
                    '--left': `${bounds.left.value}px`,
                    '--width': `${bounds.width.value}px`,
                    '--height': `${bounds.height.value}px`,
                }"
                :data-parent-id="id"
                @keydown.up.down.prevent
                @blur.capture="onBlur">
                <button
                    v-for="(option, i) in trimmedOptions"
                    :id="`${props.id}-option-${i}`"
                    :key="option"
                    :data-parent-id="props.id"
                    class="headless-multiselect__option"
                    role="option"
                    :aria-selected="props.selected.includes(option)"
                    :class="{
                        invalid: i === 0 && !searchValueValid,
                        highlighted: highlightedOption === i,
                    }"
                    @click="() => onOptionSelected(option)"
                    @keydown="(e) => onOptionKey(e, i)"
                    @mouseover="() => onOptionHover(i)"
                    @focusin="() => onOptionHover(i)"
                    @keydown.tab="(e) => onOptionTab(e, i)">
                    <span>
                        {{ option }}
                    </span>

                    <span v-if="props.selected.includes(option)" class="headless-multiselect__info">
                        <template v-if="trimmedSearchValue === option || highlightedOption === i">
                            <FontAwesomeIcon
                                class="headless-multiselect__needs-highlight"
                                icon="fa-times"
                                fixed-width />
                            <span class="sr-only">remove tag</span>
                        </template>
                        <template v-else>
                            <FontAwesomeIcon icon="fa-check" fixed-width />
                        </template>
                    </span>
                    <span v-else class="headless-multiselect__info">
                        <FontAwesomeIcon class="headless-multiselect__needs-highlight" icon="fa-plus" fixed-width />
                        <span class="sr-only">add tag</span>
                    </span>
                </button>
            </div>
        </Vue2Teleport>
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";

.headless-multiselect {
    fieldset {
        display: flex;
        flex-direction: row;
        height: 1.75rem;
        align-items: center;
    }

    input {
        text-decoration: none;
        background: none;
        border: none;
        padding-left: 0.25rem;
        flex-grow: 1;
        margin: 0;
        border: none;

        &:focus,
        &:focus-visible {
            outline: none;
            border: none;
        }
    }

    button {
        background: none;
        border: none;
        padding: 0;
        width: 2rem;
    }
}

.headless-multiselect__options {
    position: fixed;
    z-index: 10000;
    overflow-y: scroll;

    top: calc(var(--top) + var(--height));
    left: calc(var(--left) + 4px);

    width: calc(var(--width) - 4px);
    max-height: min(300px, calc(100% - var(--top) - var(--height) - 12px));

    display: flex;
    flex-direction: column;
    box-shadow: 0 0 6px 0 rgba(3, 0, 34, 0.048), 0 0 4px 0 rgba(3, 0, 34, 0.185);
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;

    .headless-multiselect__option {
        padding: 0.4rem 0.5rem;
        display: inline-block;
        text-align: start;
        background-color: $white;
        color: $brand-primary;
        border: none;
        border-radius: 0;
        font-weight: bold;
        transition: none;

        &:focus,
        &:focus-visible {
            border: none;
            outline: none;
            box-shadow: none;
        }

        &.invalid {
            color: $brand-light;
            background-color: $brand-warning;
        }

        .headless-multiselect__info {
            float: right;
        }

        .headless-multiselect__needs-highlight {
            visibility: hidden;
        }

        &.highlighted {
            background-color: $brand-primary;
            color: $white;

            .headless-multiselect__needs-highlight {
                visibility: unset;
            }
        }

        &[aria-selected].highlighted {
            background-color: $brand-danger;
        }
    }
}
</style>
