<script setup lang="ts">
/**
 * This component is only the select element of a multiselect.
 * It does not display selected options.
 * It is a building block for building a custom Multiselect,
 * not a fully featured Multiselect alternative
 */

import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faChevronUp, faPlus, faTags, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useElementBounding, whenever } from "@vueuse/core";
import { computed, nextTick, ref, watch } from "vue";
// @ts-ignore missing types
import Vue2Teleport from "vue2-teleport";

import { useUid } from "@/composables/utils/uid";
import { normalizeTag } from "@/stores/userTagsStore";

library.add(faCheck, faChevronUp, faPlus, faTags, faTimes);

const props = withDefaults(
    defineProps<{
        options: Array<string>;
        selected: Array<string>;
        maxShownOptions?: number;
        placeholder?: string;
        id?: string;
        /** adjusts the visual appearance of the search value */
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
    /** emitted when the selected options are changed */
    (e: "input", selected: string[]): void;
    /** emitted when a new option is selected, which wasn't part of the options prop */
    (e: "addOption", newOption: string): void;
    /** emitted when a option is added */
    (e: "selected", option: string): void;
}>();

const inputField = ref<HTMLInputElement | null>(null);
const openButton = ref<HTMLButtonElement | null>(null);

/** controls the open state of the select popup */
const isOpen = ref(false);

/** open popup and focus search field */
async function open() {
    isOpen.value = true;
    await nextTick();
    inputField.value?.focus();
}

/** close popup and focus open button */
async function close(refocus = true) {
    isOpen.value = false;

    if (refocus) {
        await nextTick();
        openButton.value?.focus();
    }

    searchValue.value = "";
}

/** the text in the input field */
const searchValue = ref("");
const trimmedSearchValue = computed(() => searchValue.value.trim());
const optionsAsSet = computed(() => new Set(props.options));
const searchValueEmpty = computed(() => trimmedSearchValue.value === "");
const searchValueValid = computed(() => searchValueEmpty.value || props.validator(trimmedSearchValue.value));

/** options which partially match the search value */
const filteredOptions = computed(() => {
    if (searchValueEmpty.value) {
        return props.options;
    } else {
        return props.options.filter((option) => option.includes(trimmedSearchValue.value));
    }
});

/** options trimmed to `maxShownOptions` and reordered so the search value appears first */
const trimmedOptions = computed(() => {
    const optionsSliced = filteredOptions.value
        .slice(0, props.maxShownOptions)
        .map((tag) => tag.replace(/^name:/, "#"));

    // remove search value to put it in front
    const optionsSet = new Set(optionsSliced);
    optionsSet.delete(trimmedSearchValue.value);
    const optionsTrimmed = Array.from(optionsSet);

    if (!searchValueEmpty.value) {
        optionsTrimmed.unshift(trimmedSearchValue.value);
    }

    return optionsTrimmed;
});

/** the option which will be added when the `Enter` key is pressed */
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

/** allows for selecting from the autocomplete list while focusing the input field */
function onInputUp() {
    if (highlightedOption.value > 0) {
        highlightedOption.value -= 1;
    }

    getOptionWithId(highlightedOption.value)?.scrollIntoView({ block: "center" });
}

/** allows for selecting from the autocomplete list while focusing the input field */
function onInputDown() {
    if (highlightedOption.value < trimmedOptions.value.length - 1) {
        highlightedOption.value += 1;
    }

    getOptionWithId(highlightedOption.value)?.scrollIntoView({ block: "center" });
}

/** finds the html element for the option with given id */
function getOptionWithId(id: number) {
    return document.querySelector(`#${props.id}-option-${id}`) as HTMLButtonElement | null;
}

/**
 * Emits an input event with the new selected options,
 * or emits an addOption event, if the selected option
 * was not part of the provided options
 */
function onOptionSelected(option: string) {
    option = normalizeTag(option);

    if (!optionsAsSet.value.has(option)) {
        emit("addOption", option);
        return;
    }

    const set = new Set(props.selected);

    if (set.has(option)) {
        set.delete(option);
    } else {
        set.add(option);
        emit("selected", option);
    }

    emit("input", Array.from(set));
}

/** handles the Enter key on the input element */
function onInputEnter() {
    const option = trimmedOptions.value[highlightedOption.value];

    if (option) {
        onOptionSelected(option);
        searchValue.value = "";
    }
}

/** handles keyboard navigation when the popup is focused */
function onOptionKey(event: KeyboardEvent, index: number) {
    if (event.key === "ArrowUp") {
        if (index < 1) {
            inputField.value?.focus();
        } else {
            getOptionWithId(index - 1)?.focus();
        }
    } else if (event.key === "ArrowDown") {
        getOptionWithId(index + 1)?.focus();
    } else if (event.key === "Escape") {
        close();
    }
}

/**
 * Closes popup when focus leaves this element
 * Because this component uses a Teleport, uses a custom `data-parent-id` attribute
 * to determine if the element is a child of this component
 */
function onBlur(e: FocusEvent) {
    const newTarget = e.relatedTarget;

    // close without refocusing open button
    if (!(newTarget instanceof HTMLElement)) {
        close(false);
    } else if (newTarget.getAttribute("data-parent-id") !== props.id) {
        close(false);
    }
}

/** emulates tab behavior, because options list is teleported to the app layer */
function onCloseButtonTab(event: KeyboardEvent) {
    if (!event.shiftKey) {
        getOptionWithId(0)?.focus();
        event.preventDefault();
    }
}

const closeButton = ref<HTMLButtonElement | null>(null);

/** finds and returns the next focusable element right after this component */
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

/**
 * Emulates continuous tab behavior.
 * This is required because part of the component is teleported to the app layer,
 * so this component is not continuous in the DOM
 */
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
/** used to position the pop-up */
const bounds = useElementBounding(root);

watch(
    () => [props.options, props.selected],
    async () => {
        await nextTick();
        bounds.update();
    }
);

whenever(isOpen, async () => {
    await nextTick();
    bounds.update();
});
</script>

<template>
    <div ref="root" class="headless-multiselect">
        <fieldset v-if="isOpen" @blur.capture="onBlur">
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
                @keydown.enter="onInputEnter"
                @keydown.escape="close(true)" />
            <button
                ref="closeButton"
                :data-parent-id="props.id"
                title="close"
                @click="close(true)"
                @keydown.tab="onCloseButtonTab">
                <FontAwesomeIcon icon="fa-chevron-up" />
            </button>
        </fieldset>
        <button v-else ref="openButton" class="toggle-button" @click="open">
            {{ props.placeholder }}
            <FontAwesomeIcon icon="fa-tags" />
        </button>

        <Vue2Teleport v-if="isOpen" to="#app">
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
                    :aria-selected="props.selected.includes(normalizeTag(option))"
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

                    <span v-if="props.selected.includes(normalizeTag(option))" class="headless-multiselect__info">
                        <template v-if="highlightedOption === i">
                            <FontAwesomeIcon
                                class="headless-multiselect__needs-highlight"
                                icon="fa-times"
                                fixed-width />
                            <span class="sr-only">移除标签</span>
                        </template>
                        <FontAwesomeIcon v-else icon="fa-check" fixed-width />
                    </span>
                    <span v-else class="headless-multiselect__info">
                        <FontAwesomeIcon class="headless-multiselect__needs-highlight" icon="fa-plus" fixed-width />
                        <span class="sr-only">添加标签</span>
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

    .toggle-button {
        font-size: $font-size-base;
        color: $text-color;
        text-decoration: none;
        padding: 0 0.25rem;
        background: none;
        cursor: text;
        text-align: left;
        margin: 0;
        border: none;
        width: 100%;
        height: 1.75rem;
    }
}

.headless-multiselect__options {
    position: fixed;
    z-index: 10000;
    overflow-y: scroll;

    top: 0;
    left: 0;
    transform: translate(var(--left), calc(var(--top) + var(--height)));

    width: var(--width);
    max-height: min(300px, calc(100% - var(--top) - var(--height) - 12px));

    display: flex;
    flex-direction: column;
    box-shadow: 0 0 6px 0 rgba(3, 0, 34, 0.048), 0 0 4px 0 rgba(3, 0, 34, 0.185);
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;

    background-color: $white;

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
