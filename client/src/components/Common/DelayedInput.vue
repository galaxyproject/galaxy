<script setup lang="ts">
import { faAngleDoubleDown, faAngleDoubleUp, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import localize from "@/utils/localization";

import GFormInput from "../BaseComponents/Form/GFormInput.vue";
import GButton from "../BaseComponents/GButton.vue";

interface Props {
    value?: string;
    delay?: number;
    loading?: boolean;
    placeholder?: string;
    showAdvanced?: boolean;
    enableAdvanced?: boolean;
    autocompleteValues?: string[];
    autocompletePrefix?: string;
}

interface AutocompleteMatch {
    start: number;
    end: number;
    query: string;
}

const props = withDefaults(defineProps<Props>(), {
    value: "",
    delay: 1000,
    loading: false,
    placeholder: "Enter your search term here.",
    showAdvanced: false,
    enableAdvanced: false,
    autocompleteValues: () => [],
    autocompletePrefix: "",
});

const emit = defineEmits<{
    (e: "input", value: string): void;
    (e: "change", value: string): void;
    (e: "onToggle", showAdvanced: boolean): void;
}>();

const queryInput = ref<string>();
const queryTimer = ref<ReturnType<typeof setTimeout> | null>(null);
const titleClear = ref("Clear Search (esc)");
const titleAdvanced = ref("Toggle Advanced Search");
const toolInput = ref<InstanceType<typeof GFormInput> | null>(null);
const rootEl = ref<HTMLElement | null>(null);
const selectedSuggestionIndex = ref(0);
const showSuggestions = ref(false);

function escapeRegExp(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function getInputElement() {
    return toolInput.value?.getInputElement?.() ?? null;
}

function clearTimer() {
    if (queryTimer.value) {
        clearTimeout(queryTimer.value);
    }
}

function delayQuery(query: string) {
    clearTimer();
    if (query) {
        queryTimer.value = setTimeout(() => {
            setQuery(query);
        }, props.delay);
    } else {
        setQuery(query);
    }
}

function setQuery(queryNew: string) {
    emit("input", queryNew);
    emit("change", queryNew);
}

function getAutocompleteMatch(query: string): AutocompleteMatch | null {
    const prefix = props.autocompletePrefix;
    if (!prefix || !props.autocompleteValues.length) {
        return null;
    }

    const inputElement = getInputElement();
    const caret = inputElement?.selectionStart ?? query.length;
    const beforeCaret = query.slice(0, caret);
    const afterCaret = query.slice(caret);
    const prefixPattern = escapeRegExp(prefix);
    const match = beforeCaret.match(new RegExp(`(?:^|\\s)(${prefixPattern})(?:"([^"]*)|([^\\s"]*))?$`));

    if (!match) {
        return null;
    }

    const fullMatch = match[0] ?? "";
    const leadingWhitespaceLength = fullMatch.length - fullMatch.trimStart().length;
    const start = beforeCaret.length - fullMatch.length + leadingWhitespaceLength;
    const queryPart = match[2] ?? match[3] ?? "";

    let end = caret;
    if (match[2] !== undefined) {
        const nextQuoteIndex = afterCaret.indexOf('"');
        end = nextQuoteIndex >= 0 ? caret + nextQuoteIndex + 1 : query.length;
    } else {
        const trailingToken = afterCaret.match(/^[^\s]*/)?.[0] ?? "";
        end = caret + trailingToken.length;
    }

    return {
        start,
        end,
        query: queryPart,
    };
}

function formatAutocompleteValue(value: string) {
    return /\s/.test(value) ? `"${value.replace(/"/g, '\\"')}"` : value;
}

const autocompleteMatch = computed(() => getAutocompleteMatch(queryInput.value ?? ""));

const autocompleteSuggestions = computed(() => {
    const match = autocompleteMatch.value;
    if (!match) {
        return [];
    }

    const needle = match.query.toLowerCase();
    if (needle && props.autocompleteValues.some((value) => value.toLowerCase() === needle)) {
        return [];
    }

    return [...new Set(props.autocompleteValues)]
        .filter((value) => !needle || value.toLowerCase().includes(needle))
        .sort((left, right) => {
            const leftLower = left.toLowerCase();
            const rightLower = right.toLowerCase();
            const leftStarts = leftLower.startsWith(needle);
            const rightStarts = rightLower.startsWith(needle);
            if (leftStarts !== rightStarts) {
                return leftStarts ? -1 : 1;
            }
            return left.localeCompare(right);
        })
        .slice(0, 8);
});

const activeSuggestion = computed(() => autocompleteSuggestions.value[selectedSuggestionIndex.value] ?? null);

function syncSuggestions() {
    const suggestions = autocompleteSuggestions.value;
    if (!autocompleteMatch.value || suggestions.length === 0) {
        showSuggestions.value = false;
        selectedSuggestionIndex.value = 0;
        return;
    }

    showSuggestions.value = true;
    if (selectedSuggestionIndex.value >= suggestions.length) {
        selectedSuggestionIndex.value = 0;
    }
}

async function applySuggestion(value: string) {
    const match = autocompleteMatch.value;
    if (!match) {
        return;
    }

    const prefix = props.autocompletePrefix;
    const replacementCore = `${prefix}${formatAutocompleteValue(value)}`;
    const suffix = (queryInput.value ?? "").slice(match.end);
    const needsTrailingSpace = !suffix || !/^\s/.test(suffix);
    const replacement = `${replacementCore}${needsTrailingSpace ? " " : ""}`;
    const nextValue = `${(queryInput.value ?? "").slice(0, match.start)}${replacement}${suffix}`;
    const caretPosition = match.start + replacement.length;

    queryInput.value = nextValue;
    showSuggestions.value = false;
    selectedSuggestionIndex.value = 0;

    await nextTick();
    const inputElement = getInputElement();
    inputElement?.focus();
    inputElement?.setSelectionRange(caretPosition, caretPosition);
}

function clearBox(event?: KeyboardEvent) {
    if (!event || event.key === "Escape") {
        queryInput.value = "";
        toolInput.value?.focus();
    }
}

function onToggle() {
    emit("onToggle", !props.showAdvanced);
}

function onKeydown(event: KeyboardEvent) {
    if (showSuggestions.value && autocompleteSuggestions.value.length > 0) {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            selectedSuggestionIndex.value = (selectedSuggestionIndex.value + 1) % autocompleteSuggestions.value.length;
            return;
        }
        if (event.key === "ArrowUp") {
            event.preventDefault();
            selectedSuggestionIndex.value =
                (selectedSuggestionIndex.value - 1 + autocompleteSuggestions.value.length) %
                autocompleteSuggestions.value.length;
            return;
        }
        if ((event.key === "Enter" || event.key === "Tab") && activeSuggestion.value) {
            event.preventDefault();
            void applySuggestion(activeSuggestion.value);
            return;
        }
        if (event.key === "Escape") {
            event.preventDefault();
            showSuggestions.value = false;
            selectedSuggestionIndex.value = 0;
            return;
        }
    }

    clearBox(event);
}

function onDocumentMousedown(event: MouseEvent) {
    if (!rootEl.value || !(event.target instanceof Node)) {
        return;
    }
    if (!rootEl.value.contains(event.target)) {
        showSuggestions.value = false;
    }
}

watch(
    () => queryInput.value,
    () => {
        syncSuggestions();
        delayQuery(queryInput.value ?? "");
    },
);

watch(
    () => props.autocompleteValues,
    () => {
        syncSuggestions();
    },
    { deep: true },
);

watchImmediate(
    () => props.value,
    (newQuery) => {
        queryInput.value = newQuery;
    },
);

onMounted(() => {
    document.addEventListener("mousedown", onDocumentMousedown);
});

onBeforeUnmount(() => {
    document.removeEventListener("mousedown", onDocumentMousedown);
});
</script>

<template>
    <div ref="rootEl" class="delayed-input">
        <BInputGroup>
            <GFormInput
                ref="toolInput"
                v-model="queryInput"
                class="search-query form-control"
                autocomplete="off"
                :placeholder="placeholder"
                data-description="filter text input"
                @keydown="onKeydown" />

            <BInputGroupAppend>
                <GButton
                    v-if="enableAdvanced"
                    tooltip
                    aria-haspopup="true"
                    size="small"
                    :pressed="showAdvanced"
                    :color="showAdvanced ? 'blue' : 'grey'"
                    :title="localize(titleAdvanced)"
                    data-description="toggle advanced search"
                    @click="onToggle">
                    <FontAwesomeIcon v-if="showAdvanced" fixed-width :icon="faAngleDoubleUp" />
                    <FontAwesomeIcon v-else fixed-width :icon="faAngleDoubleDown" />
                </GButton>

                <GButton
                    tooltip
                    aria-haspopup="true"
                    class="search-clear"
                    size="small"
                    :title="localize(titleClear)"
                    data-description="reset query"
                    @click="clearBox(undefined)">
                    <FontAwesomeIcon v-if="loading" fixed-width :icon="faSpinner" spin />
                    <FontAwesomeIcon v-else fixed-width :icon="faTimes" />
                </GButton>
            </BInputGroupAppend>
        </BInputGroup>

        <div v-if="showSuggestions" class="autocomplete-suggestions" data-description="search-autocomplete">
            <button
                v-for="(suggestion, index) in autocompleteSuggestions"
                :key="suggestion"
                type="button"
                :class="[
                    'autocomplete-suggestion',
                    { 'autocomplete-suggestion-active': index === selectedSuggestionIndex },
                ]"
                @mousedown.prevent="applySuggestion(suggestion)">
                <span class="autocomplete-prefix">{{ props.autocompletePrefix }}</span>
                <span class="autocomplete-value">{{ formatAutocompleteValue(suggestion) }}</span>
            </button>
        </div>
    </div>
</template>

<style scoped lang="scss">
.delayed-input {
    position: relative;
}

.autocomplete-suggestions {
    background: var(--white);
    border: 1px solid var(--color-grey-300);
    border-radius: var(--spacing-1);
    box-shadow: 0 0.375rem 1rem rgb(0 0 0 / 0.14);
    inset: calc(100% + 0.25rem) 0 auto 0;
    overflow: hidden;
    position: absolute;
    z-index: 1200;
}

.autocomplete-suggestion {
    align-items: center;
    background: transparent;
    border: 0;
    color: inherit;
    cursor: pointer;
    display: flex;
    gap: 0.25rem;
    padding: 0.375rem 0.625rem;
    text-align: left;
    width: 100%;
}

.autocomplete-suggestion:hover,
.autocomplete-suggestion-active {
    background: var(--color-blue-100);
}

.autocomplete-prefix {
    color: var(--color-blue-700);
    font-weight: 600;
}

.autocomplete-value {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
