<script setup lang="ts">
import { faSearch, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventListener, watchDebounced, watchImmediate } from "@vueuse/core";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { useCommandPalette } from "@/composables/useCommandPalette";
import { useUid } from "@/composables/utils/uid";
import { useEventStore } from "@/stores/eventStore";
import { useToolStore } from "@/stores/toolStore";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { useUserStore } from "@/stores/userStore";
import { localize } from "@/utils/localization";

import { findPaletteProvider, paletteProviders, rankPaletteItems } from "./providers";
import { ACTIONS_SCOPE, availableScopes, type ScopeDefinition } from "./providers/scopes";
import type { PaletteContext, PaletteItem } from "./types";
import { type PaletteMode, usePaletteMachine } from "./usePaletteMachine";
import { scorePaletteItems } from "./utilities";

import CommandPaletteItem from "./CommandPaletteItem.vue";

const SEARCH_DEBOUNCE = 150;
/** Cap per section on an empty query so defaults stay scannable */
const MAX_EMPTY_QUERY_ITEMS = 8;
/** Safety net for environments that never fire `transitionend` (jsdom, backgrounded tabs) */
const CLOSE_TRANSITION_FALLBACK = 200;

const ROOT_PLACEHOLDER = "Search Galaxy…  (> actions, w: t: … scopes, ? help)";

interface ResultSection {
    id: string;
    items: PaletteItem[];
    title: string;
}

const { isPaletteOpen, closePalette, togglePalette } = useCommandPalette();
const router = useRouter();
const { config } = useConfig();
const eventStore = useEventStore();
const toolStore = useToolStore();
const unprivilegedToolStore = useUnprivilegedToolStore();
const userStore = useUserStore();

const { badgeLabel, enterScope, handleEscape, mode, popMode, query, reset, setText, text } = usePaletteMachine();

const dialogElement = ref<HTMLDialogElement | null>(null);
const inputElement = ref<HTMLInputElement | null>(null);
const searching = ref(false);
const sections = ref<ResultSection[]>([]);
const selectedIndex = ref(0);
/** Scope whose provider has not landed yet; renders the temporary hint row */
const pendingScope = ref<ScopeDefinition | null>(null);

const uid = useUid("command-palette");
const listboxId = computed(() => `${uid.value}-listbox`);

const flatItems = computed(() => sections.value.flatMap((section) => section.items));

const selectedItem = computed(() => flatItems.value[selectedIndex.value]);

const activeDescendant = computed(() => (selectedItem.value ? optionId(selectedIndex.value) : undefined));

const modifierLabel = computed(() => (eventStore.isMac ? "⌘" : "Ctrl+"));

const badgeAriaLabel = computed(() => `${localize("Remove filter")}: ${badgeLabel.value}`);

const placeholder = computed(() => {
    const activeMode = mode.value;
    if (activeMode.type === "action") {
        return activeMode.action.argumentMode?.placeholder ?? searchLabel(activeMode.action.title);
    }
    if (activeMode.type === "scoped") {
        return searchLabel(localize(activeMode.scope.label));
    }
    return localize(ROOT_PLACEHOLDER);
});

const scopeHint = computed(() => {
    const scope = pendingScope.value;
    if (!scope) {
        return undefined;
    }
    return `${scope.key}: ${localize("searches")} ${localize(scope.label)} — ${localize("provider loading soon")}`;
});

function searchLabel(subject: string) {
    return `${localize("Search")} ${subject.toLowerCase()}…`;
}

function optionId(index: number) {
    return `${uid.value}-option-${index}`;
}

function optionIndex(sectionIndex: number, itemIndex: number) {
    let offset = 0;
    for (let i = 0; i < sectionIndex; i++) {
        offset += sections.value[i]?.items.length ?? 0;
    }
    return offset + itemIndex;
}

function buildContext(): PaletteContext {
    return {
        canUseUnprivilegedTools: unprivilegedToolStore.canUseUnprivilegedTools ?? false,
        config: {
            interactivetools_enable: config.value?.interactivetools_enable,
            llm_api_configured: config.value?.llm_api_configured,
        },
        isAdmin: userStore.isAdmin,
        isAnonymous: userStore.isAnonymous,
    };
}

/** One help row per scope, selecting it turns the scope into a badge */
function scopeHelpItem(scope: ScopeDefinition): PaletteItem {
    return {
        id: `help:${scope.key}`,
        handler: () => enterScope(scope),
        keywords: scope.key,
        shortcut: scope.key === ACTIONS_SCOPE.key ? scope.key : `${scope.key}:`,
        title: `${localize("Search")} ${localize(scope.label).toLowerCase()}`,
    };
}

function helpSections(ctx: PaletteContext): ResultSection[] {
    return [
        { id: "help:actions", items: [scopeHelpItem(ACTIONS_SCOPE)], title: localize("Actions") },
        { id: "help:scopes", items: availableScopes(ctx).map(scopeHelpItem), title: localize("Scopes") },
    ].map((section) => ({ ...section, items: rankPaletteItems(section.items, query.value) }));
}

async function providerItems(providerId: string, ctx: PaletteContext): Promise<PaletteItem[]> {
    const provider = findPaletteProvider(providerId);
    if (!provider) {
        return [];
    }
    if (!query.value && provider.emptyQueryItems) {
        return provider.emptyQueryItems(ctx).slice(0, MAX_EMPTY_QUERY_ITEMS);
    }
    return provider.search(query.value, ctx);
}

/** Unscoped search: every provider contributes a section, best match first */
async function rootSections(ctx: PaletteContext): Promise<ResultSection[]> {
    const scored = await Promise.all(
        paletteProviders.map(async (provider) => {
            const items = await providerItems(provider.id, ctx);
            // sections are shown best-match first; backend-ranked tools carry
            // no scores, so they slot between "starts with" (4) and plain name
            // matches (3) of the local providers
            let score = 0;
            if (query.value) {
                score =
                    provider.id === "tools"
                        ? 3.5
                        : Math.max(0, ...scorePaletteItems(items, query.value).map((match) => match.order));
            }
            return { id: provider.id, items, score, title: provider.title };
        }),
    );
    return scored.sort((a, b) => b.score - a.score).map(({ score: _score, ...section }) => section);
}

async function scopedSections(scope: ScopeDefinition, ctx: PaletteContext): Promise<ResultSection[]> {
    const provider = findPaletteProvider(scope.providerId);
    // a variant (shared, published, …) can only be served by a scoped search
    if (!provider || (scope.variant && !provider.searchScoped)) {
        pendingScope.value = scope;
        return [];
    }
    if (provider.searchScoped) {
        const scoped = await provider.searchScoped(scope, query.value, ctx);
        return scoped.map((section) => ({ ...section, id: `${provider.id}:${section.id}` }));
    }
    return [{ id: provider.id, items: await providerItems(provider.id, ctx), title: provider.title }];
}

function modeSections(activeMode: PaletteMode, ctx: PaletteContext): Promise<ResultSection[]> | ResultSection[] {
    switch (activeMode.type) {
        case "help":
            return helpSections(ctx);
        case "action":
            // action arguments are wired up with the actions rework
            return [];
        case "scoped":
            return scopedSections(activeMode.scope, ctx);
        default:
            return rootSections(ctx);
    }
}

let searchEpoch = 0;

async function runSearch() {
    const epoch = ++searchEpoch;
    const ctx = buildContext();
    pendingScope.value = null;
    searching.value = true;
    try {
        const results = await modeSections(mode.value, ctx);
        if (epoch === searchEpoch) {
            sections.value = results.filter((section) => section.items.length > 0);
            selectedIndex.value = 0;
        }
    } finally {
        if (epoch === searchEpoch) {
            searching.value = false;
        }
    }
}

function runItem(item: PaletteItem | undefined, event?: KeyboardEvent | MouseEvent) {
    if (!item) {
        return;
    }
    if (mode.value.type === "help") {
        // help rows only rewrite the input, the palette stays open
        item.handler?.();
        return;
    }
    if (item.to) {
        const newTab = Boolean(event && (event.ctrlKey || event.metaKey));
        if (newTab) {
            window.open(router.resolve(item.to).href, "_blank", "noopener");
        } else {
            router.push(item.to).catch(() => {
                // duplicate navigation to the current route is fine
            });
        }
    } else {
        item.handler?.();
    }
    closePalette();
}

function onInput(event: Event) {
    const input = event.target as HTMLInputElement;
    setText(input.value);
    if (input.value !== text.value) {
        // a recognized token was converted into a badge
        input.value = text.value;
    }
}

function dismissBadge() {
    popMode();
    inputElement.value?.focus();
}

function onKeydown(event: KeyboardEvent) {
    const count = flatItems.value.length;
    switch (event.key) {
        case "ArrowDown":
            event.preventDefault();
            if (count > 0) {
                selectedIndex.value = (selectedIndex.value + 1) % count;
            }
            break;
        case "ArrowUp":
            event.preventDefault();
            if (count > 0) {
                selectedIndex.value = (selectedIndex.value - 1 + count) % count;
            }
            break;
        case "Backspace": {
            const input = event.target as HTMLInputElement;
            if (mode.value.type !== "root" && input.selectionStart === 0 && input.selectionEnd === 0) {
                event.preventDefault();
                popMode();
            }
            break;
        }
        case "Enter":
            event.preventDefault();
            runItem(selectedItem.value, event);
            break;
        case "Escape":
            event.preventDefault();
            if (handleEscape() === "close") {
                closePalette();
            }
            break;
    }
}

function onClickDialog(event: MouseEvent) {
    if ((event.target as HTMLElement | null)?.tagName === "DIALOG") {
        const rect = dialogElement.value?.getBoundingClientRect();
        const insideX = rect && event.clientX >= rect.left && event.clientX <= rect.right;
        const insideY = rect && event.clientY >= rect.top && event.clientY <= rect.bottom;
        if (!(insideX && insideY)) {
            closePalette();
        }
    }
}

function onDialogClose() {
    if (isPaletteOpen.value) {
        closePalette();
    }
}

watch(selectedIndex, () => {
    if (selectedItem.value) {
        document.getElementById(optionId(selectedIndex.value))?.scrollIntoView({ block: "nearest" });
    }
});

useEventListener(window, "keydown", (event: KeyboardEvent) => {
    const platformModifier = eventStore.isMac ? event.metaKey : event.ctrlKey;
    if (event.key.toLowerCase() === "k" && platformModifier && !event.shiftKey && !event.altKey && !event.repeat) {
        event.preventDefault();
        togglePalette();
    }
});

watchDebounced([text, mode], runSearch, { debounce: SEARCH_DEBOUNCE });

/** Drives the enter/leave transition; the dialog element itself stays mounted */
const paletteVisible = ref(false);
/** Bumped by every open and close so a rapid toggle cancels the transition in flight */
let transitionEpoch = 0;
let closeTimeout: ReturnType<typeof setTimeout> | null = null;

function prefersReducedMotion() {
    return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Two frames: the first paints the closed state, the second starts the transition */
function afterNextFrame(callback: () => void) {
    if (typeof requestAnimationFrame !== "function") {
        callback();
        return;
    }
    requestAnimationFrame(() => requestAnimationFrame(callback));
}

function clearCloseTimeout() {
    if (closeTimeout !== null) {
        clearTimeout(closeTimeout);
        closeTimeout = null;
    }
}

async function openDialog() {
    const epoch = ++transitionEpoch;
    // a close still waiting on its transition must not fire after we reopen
    clearCloseTimeout();
    await nextTick();
    const dialog = dialogElement.value;
    if (!dialog || epoch !== transitionEpoch) {
        return;
    }
    if (!dialog.open) {
        try {
            dialog.showModal();
        } catch (e) {
            // dialog may already be open, or the test environment lacks support
        }
    }
    inputElement.value?.focus();
    if (prefersReducedMotion()) {
        paletteVisible.value = true;
        return;
    }
    afterNextFrame(() => {
        if (epoch === transitionEpoch) {
            paletteVisible.value = true;
        }
    });
}

function closeDialog() {
    const epoch = ++transitionEpoch;
    clearCloseTimeout();
    paletteVisible.value = false;
    const dialog = dialogElement.value;
    if (!dialog?.open) {
        return;
    }
    function finishClose() {
        dialog?.removeEventListener("transitionend", onTransitionEnd);
        if (epoch !== transitionEpoch) {
            // reopened mid-transition, the newer open owns the dialog now
            return;
        }
        clearCloseTimeout();
        dialog?.close();
    }
    function onTransitionEnd(event: TransitionEvent) {
        if (event.target === dialog) {
            finishClose();
        }
    }
    if (prefersReducedMotion()) {
        finishClose();
        return;
    }
    dialog.addEventListener("transitionend", onTransitionEnd);
    closeTimeout = setTimeout(finishClose, CLOSE_TRANSITION_FALLBACK);
}

onBeforeUnmount(() => {
    transitionEpoch++;
    clearCloseTimeout();
});

watchImmediate(isPaletteOpen, (open) => {
    if (open) {
        reset();
        // hydrate the tool store so recent tools resolve to names
        toolStore.fetchTools()?.catch?.(() => {});
        runSearch();
        openDialog();
    } else {
        closeDialog();
    }
});
</script>

<template>
    <!-- Clicking the backdrop is a mouse-only close shortcut; keyboard users have escape -->
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions, vuejs-accessibility/click-events-have-key-events -->
    <dialog
        ref="dialogElement"
        class="command-palette"
        :class="{ 'palette-open': paletteVisible }"
        aria-label="Command palette"
        @click="onClickDialog"
        @close="onDialogClose">
        <div class="palette-input">
            <FontAwesomeIcon
                class="palette-input-icon"
                fixed-width
                :icon="searching ? faSpinner : faSearch"
                :spin="searching" />

            <button
                v-if="badgeLabel"
                class="palette-badge"
                type="button"
                data-description="palette badge"
                :aria-label="badgeAriaLabel"
                @click="dismissBadge">
                {{ badgeLabel }}

                <FontAwesomeIcon :icon="faTimes" />
            </button>

            <input
                ref="inputElement"
                data-description="palette input"
                type="text"
                role="combobox"
                autocomplete="off"
                spellcheck="false"
                aria-label="Search Galaxy"
                aria-haspopup="listbox"
                aria-expanded="true"
                :placeholder="placeholder"
                :value="text"
                :aria-controls="listboxId"
                :aria-activedescendant="activeDescendant"
                @input="onInput"
                @keydown="onKeydown" />
        </div>

        <div :id="listboxId" class="palette-results" role="listbox" aria-label="Search results">
            <div
                v-for="(section, sectionIdx) in sections"
                :key="section.id"
                role="group"
                :aria-label="section.title"
                :data-description="`palette section ${section.id}`">
                <div class="palette-section-title" aria-hidden="true">{{ section.title }}</div>

                <CommandPaletteItem
                    v-for="(item, itemIdx) in section.items"
                    :id="optionId(optionIndex(sectionIdx, itemIdx))"
                    :key="item.id"
                    :active="optionIndex(sectionIdx, itemIdx) === selectedIndex"
                    :item="item"
                    @select="runItem(item, $event)"
                    @highlight="selectedIndex = optionIndex(sectionIdx, itemIdx)" />
            </div>

            <div v-if="scopeHint" class="palette-hint" data-description="palette scope hint">
                {{ scopeHint }}
            </div>

            <div v-else-if="flatItems.length === 0 && !searching" class="palette-hint" data-description="palette empty">
                {{ localize("No results.") }}
            </div>
        </div>

        <div class="palette-footer">
            <span><kbd>↑↓</kbd> navigate</span>

            <span><kbd>↵</kbd> open</span>

            <span
                ><kbd>{{ modifierLabel }}↵</kbd> new tab</span
            >

            <span v-if="badgeLabel"><kbd>⌫</kbd> remove filter</span>

            <span><kbd>esc</kbd> clear/close</span>

            <span><kbd>?</kbd> help</span>
        </div>
    </dialog>
</template>

<style scoped lang="scss">
// Firefox ESR is still in the browserslist target, so the enter transition is
// driven by a class toggled after two frames rather than by @starting-style
$palette-transition: 130ms ease-out;

.command-palette {
    width: min(40rem, calc(100vw - 2rem));
    margin-top: 15vh;
    margin-bottom: auto;
    padding: 0;
    border: none;
    border-radius: var(--spacing-2);
    overflow: hidden;
    box-shadow: 0 18px 50px rgba(33, 37, 50, 0.35);

    background-color: var(--background-color);

    opacity: 0;
    transform: scale(0.98);
    transition:
        opacity $palette-transition,
        transform $palette-transition;

    // same backdrop treatment as GModal
    &::backdrop {
        background-color: var(--color-blue-800);
        opacity: 0;
        transition: opacity $palette-transition;
    }

    &.palette-open {
        opacity: 1;
        transform: scale(1);

        &::backdrop {
            opacity: 0.33;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        transform: none;
        transition: none;

        &::backdrop {
            transition: none;
        }
    }

    .palette-input {
        display: flex;
        align-items: center;
        gap: var(--spacing-2);
        padding: var(--spacing-3);
        border-bottom: 1px solid var(--color-grey-200);

        .palette-input-icon {
            color: var(--color-grey-500);
        }

        .palette-badge {
            display: flex;
            align-items: center;
            gap: var(--spacing-1);
            flex: none;
            padding: 0 var(--spacing-2);
            border: 1px solid var(--color-blue-300);
            border-radius: var(--spacing-2);
            background-color: var(--color-blue-100);
            color: var(--color-blue-800);
            font-size: var(--font-size-small);
            white-space: nowrap;
        }

        input {
            flex-grow: 1;
            min-width: 0;
            border: none;
            outline: none;
            background: transparent;
            color: inherit;

            &::placeholder {
                color: var(--color-grey-400);
            }
        }
    }

    .palette-results {
        max-height: 21rem;
        overflow-y: auto;
        padding-bottom: var(--spacing-1);

        .palette-section-title {
            font-size: var(--font-size-small);
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--color-grey-500);
            padding: var(--spacing-2) var(--spacing-3) var(--spacing-1);
        }

        .palette-hint {
            padding: var(--spacing-3);
            text-align: center;
            color: var(--color-grey-600);
        }
    }

    .palette-footer {
        display: flex;
        gap: var(--spacing-3);
        padding: var(--spacing-1) var(--spacing-3);
        background-color: var(--color-grey-100);
        border-top: 1px solid var(--color-grey-200);
        color: var(--color-grey-600);
        font-size: var(--font-size-small);

        kbd {
            background-color: var(--background-color);
            border: 1px solid var(--color-grey-300);
            border-radius: var(--spacing);
            color: var(--color-grey-600);
            font-size: inherit;
            padding: 0 var(--spacing-1);
        }
    }
}
</style>
