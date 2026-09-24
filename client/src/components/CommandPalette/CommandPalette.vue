<script setup lang="ts">
import {
    faQuestionCircle,
    faSearch,
    faSignInAlt,
    faSpinner,
    faTimes,
    faUserPlus,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { useStartNewChat } from "@/components/GalaxyAI/useStartNewChat";
import { useFilteredUploadMethods } from "@/components/Panels/Upload/uploadMethodRegistry";
import { getOIDCIdpsWithRegistration } from "@/components/User/ExternalIdentities/ExternalIDHelper";
import { useConfig } from "@/composables/config";
import { useCommandPalette } from "@/composables/useCommandPalette";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { useUid } from "@/composables/utils/uid";
import { useToolStore } from "@/stores/toolStore";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { useUserStore } from "@/stores/userStore";
import { localize } from "@/utils/localization";

import { ALL_CATEGORY, availableCategories, type PaletteCategory } from "./providers/categories";
import { isScopeLoginGated } from "./providers/scopes";
import type { PaletteContext, PaletteItem, ResultSection } from "./types";
import { usePaletteDialog } from "./usePaletteDialog";
import { OPTIONAL_HINTS, secondaryLabelFor, usePaletteFooter } from "./usePaletteFooter";
import { usePaletteMachine } from "./usePaletteMachine";
import { usePaletteModifiers } from "./usePaletteModifiers";
import { CATEGORY_ROW_INDEX, usePaletteSearch } from "./usePaletteSearch";
import { useScrollEdges } from "./useScrollEdges";
import { parsePaletteQuery } from "./utilities";

import CommandPaletteItem from "./CommandPaletteItem.vue";

/** Placeholder rows standing in for a provider that has not answered yet */
const SKELETON_ROWS = 3;

const { isPaletteOpen, closePalette, togglePalette } = useCommandPalette();
const { addRecentItem } = useRecentPaletteItems();
// these composables need a component instance, so the palette resolves them once
// and hands them to the providers through the context
const uploadMethods = useFilteredUploadMethods();
const startNewChat = useStartNewChat();
const route = useRoute();
const router = useRouter();
const { config } = useConfig();
const toolStore = useToolStore();
const unprivilegedToolStore = useUnprivilegedToolStore();
const userStore = useUserStore();

// the machine needs the context to reject scope tokens the user may not use;
// `buildContext` is a hoisted declaration, so it is safe to hand over here
const {
    badgeLabel,
    category: activeCategory,
    enterAction,
    enterScope,
    exitAction,
    handleEscape,
    mode,
    popMode,
    query,
    selectCategory: narrowToCategory,
    setText,
    text,
} = usePaletteMachine(buildContext);

const dialogElement = ref<HTMLDialogElement | null>(null);
const inputElement = ref<HTMLInputElement | null>(null);
const resultsElement = ref<HTMLElement | null>(null);
const categoriesElement = ref<HTMLElement | null>(null);
const { closeDialog, onClickDialog, onDialogCancel, onDialogClose, onDialogMousedown, openDialog, paletteVisible } =
    usePaletteDialog({ closePalette, dialogElement, handleEscape, inputElement, isPaletteOpen, resultsElement });
const { fadeEnd, fadeStart, revealChild } = useScrollEdges(categoriesElement);
const { modifierHeld, modifierLabel, releaseModifiers, shiftHeld } = usePaletteModifiers(togglePalette);

const uid = useUid("command-palette");
const listboxId = computed(() => `${uid.value}-listbox`);

/** Where a login has to land the user again once it is done */
const loginRedirect = computed(() => `/login/start?redirect=${encodeURIComponent(route.fullPath)}`);

/**
 * Where "Create a Galaxy account" leads, or nothing where the instance registers
 * no one. The masthead's Register button decides it the same way (see
 * `performRegistration` there): an instance that creates no local accounts still
 * registers through OIDC, and a single provider offering it is gone to directly.
 */
const registrationTarget = computed<string | undefined>(() => {
    if (config.value.allow_local_account_creation) {
        return "/register/start";
    }
    const endpoints = Object.values(getOIDCIdpsWithRegistration(config.value.oidc ?? {})).map(
        (idp) => idp.end_user_registration_endpoint,
    );
    if (endpoints.length === 0) {
        return undefined;
    }
    // several providers need the form to pick one, a single one does not
    return endpoints.length === 1 ? endpoints[0] : "/register/start";
});

/**
 * The way in for an anonymous visitor who typed a scope only an account reaches.
 * The machine refuses the badge for such a token, so it is still sitting in the
 * input to be read here — and the offer is a section of ordinary rows rather
 * than a banner, so ↑↓ and enter reach it like any other result.
 */
const loginPromptSection = computed<ResultSection | undefined>(() => {
    if (mode.value.type !== "root") {
        return undefined;
    }
    const parsed = parsePaletteQuery(text.value);
    const ctx = buildContext();
    if (parsed.type !== "scope" || !isScopeLoginGated(parsed.scope, ctx)) {
        return undefined;
    }
    const items: PaletteItem[] = [
        {
            id: "login-prompt:login",
            icon: faSignInAlt,
            title: `${localize("Log in to search")} ${localize(parsed.scope.label).toLowerCase()}`,
            to: loginRedirect.value,
        },
    ];
    // registering is offered exactly where the masthead offers it
    const registration = registrationTarget.value;
    if (registration) {
        items.push({
            id: "login-prompt:register",
            icon: faUserPlus,
            title: localize("Create a Galaxy account"),
            // an OIDC registration endpoint is off-app, so the router cannot go there
            ...(registration.startsWith("/")
                ? { to: registration }
                : {
                      handler: () => {
                          window.location.assign(registration);
                      },
                  }),
        });
    }
    return { id: "login-prompt", items, title: "Log in required" };
});

const {
    categoryRowSelected,
    failedSubject,
    highlightItem,
    moveSelection,
    pendingScope,
    runSearch,
    searching,
    selectedIndex,
    selectedItem,
    showCategoryRow,
    visibleSections,
} = usePaletteSearch({
    activeCategory,
    buildContext,
    helpHandlers: { enterScope, popMode, setText },
    leadingSection: loginPromptSection,
    mode,
    modifierLabel,
    query,
    text,
});

const activeDescendant = computed(() => (selectedItem.value ? optionId(selectedIndex.value) : undefined));

const paletteCategories = computed(() => availableCategories(buildContext()));

const activeCategoryId = computed(() => activeCategory.value?.id ?? ALL_CATEGORY.id);

/** Badge text, localized here because the providers keep their strings in English */
const badgeText = computed(() => (badgeLabel.value ? localize(badgeLabel.value) : undefined));

const badgeAriaLabel = computed(() => `${localize("Remove filter")}: ${badgeText.value}`);

const { footerHints, placeholder } = usePaletteFooter({
    categoryRowSelected,
    mode,
    modifierHeld,
    modifierLabel,
    placeholderPhrase: computed(() => config.value?.command_palette_placeholder),
    selectedItem,
    shiftHeld,
    showCategoryRow,
    text,
});

/** A running search still owns the icon; help mode otherwise names itself */
const inputIcon = computed(() => {
    if (searching.value) {
        return faSpinner;
    }
    return mode.value.type === "help" ? faQuestionCircle : faSearch;
});

const scopeHint = computed(() => {
    const scope = pendingScope.value;
    if (!scope) {
        return undefined;
    }
    return `${localize(scope.label)} — ${localize("this filter has no results provider yet.")}`;
});

/**
 * Prompt for a free text argument that has nothing to offer until something is
 * typed, so the mode asks for a value instead of reporting no results. The
 * providers are handed the trimmed text, so whitespace alone is still nothing
 * typed and has to keep asking rather than report an empty result.
 */
const argumentHint = computed(() => {
    const activeMode = mode.value;
    if (activeMode.type !== "action" || query.value !== "") {
        return undefined;
    }
    const hint = activeMode.action.argumentMode?.emptyHint;
    return hint ? localize(hint) : undefined;
});

/** Says a scope is broken rather than empty, once its very first fetch failed */
const errorHint = computed(() => {
    const subject = failedSubject.value;
    return subject ? `${localize("Couldn't load")} ${subject}. ${localize("Try again.")}` : undefined;
});

function optionId(index: number) {
    return `${uid.value}-option-${index}`;
}

function optionIndex(sectionIndex: number, itemIndex: number) {
    let offset = 0;
    for (let i = 0; i < sectionIndex; i++) {
        offset += visibleSections.value[i]?.items.length ?? 0;
    }
    return offset + itemIndex;
}

function buildContext(): PaletteContext {
    return {
        canUseUnprivilegedTools: unprivilegedToolStore.canUseUnprivilegedTools ?? false,
        config: {
            allow_local_account_creation: config.value?.allow_local_account_creation,
            // an unset list arrives as null, so it is normalized once here
            command_palette_disabled_providers: config.value?.command_palette_disabled_providers ?? [],
            enable_notification_system: config.value?.enable_notification_system,
            interactivetools_enable: config.value?.interactivetools_enable,
            llm_api_configured: config.value?.llm_api_configured,
        },
        isAnonymous: userStore.isAnonymous,
        navigate: (to: string) => {
            router.push(to).catch(() => {
                // duplicate navigation to the current route is fine
            });
        },
        startNewChat,
        uploadMethods: uploadMethods.value,
    };
}

/**
 * Remembers an opened entity so its provider can offer it in a "Recent"
 * section next time. Only items declaring an `mru` identity are recorded —
 * tools keep their own recent list in `userStore`.
 */
function recordRecentItem(item: PaletteItem) {
    if (!item.mru) {
        return;
    }
    addRecentItem({ ...item.mru, name: item.title, ...(item.to ? { to: item.to } : {}) });
}

/**
 * Shift+enter runs the secondary behavior of the selected item: an action that
 * takes an argument turns into a badge collecting it, every other item runs its
 * `secondaryAction`. An item offering neither ignores the key.
 */
function runSecondary(item: PaletteItem) {
    if (item.argumentMode) {
        enterAction(item);
        return;
    }
    const secondary = item.secondaryAction;
    if (!secondary) {
        return;
    }
    recordRecentItem(item);
    if (secondary.to) {
        router.push(secondary.to).catch(() => {
            // duplicate navigation to the current route is fine
        });
    } else {
        secondary.run?.(buildContext());
    }
    closePalette();
}

/**
 * Hands typing back to the combobox. A row activated with the mouse leaves the
 * focus on the clicked element, so every path that keeps the palette open has
 * to return it — otherwise the keyboard is dead until the input is clicked.
 */
function refocusInput() {
    if (isPaletteOpen.value) {
        inputElement.value?.focus();
    }
}

function runItem(item: PaletteItem | undefined, event?: KeyboardEvent | MouseEvent) {
    if (!item) {
        return;
    }
    if (mode.value.type === "help") {
        // help rows only rewrite the input, the palette stays open
        item.handler?.(buildContext());
        refocusInput();
        return;
    }
    if (event?.shiftKey || item.argumentMode?.immediate) {
        // an action without a useful default enters its argument mode on plain enter too
        runSecondary(item);
        // no-op once the secondary closed the palette
        refocusInput();
        return;
    }
    // an item sent to a new tab counts as opened just as much as a navigation
    recordRecentItem(item);
    if (item.to) {
        if (event && (event.ctrlKey || event.metaKey)) {
            // the palette stays open so several items can be sent to tabs in a row
            window.open(router.resolve(item.to).href, "_blank", "noopener");
            refocusInput();
            return;
        }
        router.push(item.to).catch(() => {
            // duplicate navigation to the current route is fine
        });
    } else {
        item.handler?.(buildContext());
    }
    closePalette();
}

/** Previews what ctrl/cmd + enter would do on the selected, navigable item */
function showExternalIcon(index: number, item: PaletteItem) {
    return modifierHeld.value && !shiftHeld.value && index === selectedIndex.value && Boolean(item.to);
}

/** Previews what `⇧↵` would do on the selected item, so a row never claims both */
function secondaryHint(index: number, item: PaletteItem) {
    return shiftHeld.value && index === selectedIndex.value ? secondaryLabelFor(item) : undefined;
}

function onInput(event: Event) {
    const input = event.target as HTMLInputElement;
    // read before the text changes: emptying the query — or typing a scope
    // token — hides the category row, and the selection would then be stranded
    // on a row that no longer exists, leaving enter with nothing to run
    const leavingCategoryRow = categoryRowSelected.value;
    setText(input.value);
    if (input.value !== text.value) {
        // a recognized token was converted into a badge
        input.value = text.value;
    }
    if (leavingCategoryRow) {
        // typing is about the results again, so the selection returns to them
        selectedIndex.value = 0;
    }
}

/**
 * Moving onto a category applies it right away, no confirmation needed. The
 * rerun rides the shared debounce, so holding ←→ across the row costs one
 * search instead of one per category passed over.
 */
function selectCategory(category: PaletteCategory) {
    narrowToCategory(category);
    // after the narrowing, which cleared the rows and the selection with them
    selectedIndex.value = CATEGORY_ROW_INDEX;
}

/** The row is keyboard driven, so a clicked chip hands the focus straight back */
function onCategoryClick(category: PaletteCategory) {
    selectCategory(category);
    refocusInput();
}

function moveCategory(delta: 1 | -1) {
    const categories = paletteCategories.value;
    const current = categories.findIndex((category) => category.id === activeCategoryId.value);
    const next = categories[(Math.max(current, 0) + delta + categories.length) % categories.length];
    if (next) {
        selectCategory(next);
    }
}

function dismissBadge() {
    popMode();
    inputElement.value?.focus();
}

function onKeydown(event: KeyboardEvent) {
    switch (event.key) {
        case "ArrowDown":
            event.preventDefault();
            moveSelection(1);
            break;
        case "ArrowUp":
            event.preventDefault();
            moveSelection(-1);
            break;
        case "ArrowLeft":
        case "ArrowRight":
            // hijacked only while the category row is selected — everywhere else
            // the arrows keep moving the caret through the typed text
            if (categoryRowSelected.value) {
                event.preventDefault();
                moveCategory(event.key === "ArrowRight" ? 1 : -1);
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
            if (categoryRowSelected.value) {
                // the category is already applied, enter just returns to the list
                selectedIndex.value = 0;
                break;
            }
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

watch(selectedIndex, () => {
    if (selectedItem.value) {
        document.getElementById(optionId(selectedIndex.value))?.scrollIntoView({ block: "nearest" });
    }
});

// ←→ can land on a chip scrolled out of the row, and the row can reappear on a narrowed category
watch(
    [activeCategoryId, showCategoryRow],
    () => revealChild(categoriesElement.value?.querySelector(".palette-category.active")),
    { flush: "post" },
);

/** Bumped by every open, so a hydration landing after a close is dropped */
let openEpoch = 0;
/** Whether the one-off tool store hydration already succeeded this session */
let toolsHydrated = false;

/**
 * Fills the tool store on the first open so recent tools resolve to names, then
 * reruns the search that was already answered from the empty cache. Guarded by
 * both the epoch and the flag, so it can never rerun more than once per open
 * and never at all once the store is filled.
 */
async function hydrateTools() {
    if (toolsHydrated) {
        return;
    }
    const epoch = openEpoch;
    try {
        await toolStore.fetchTools();
    } catch (e) {
        // a failed hydration is retried the next time the palette opens
        return;
    }
    toolsHydrated = true;
    if (epoch === openEpoch && isPaletteOpen.value) {
        runSearch();
    }
}

// what was typed survives a close, so a ⌘K toggle or a stray backdrop click can
// be taken back: only escape clears the palette, one step at a time, and by the
// time it asks for the close there is nothing left to preserve
watchImmediate(isPaletteOpen, (open) => {
    if (open) {
        openEpoch++;
        hydrateTools();
        runSearch();
        openDialog();
    } else {
        releaseModifiers();
        // the one exception to preserving the input: an action's argument mode
        // parses nothing, so a `>` typed into a reopened palette would be
        // collected as the argument instead of opening the actions list
        exitAction();
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
        :aria-label="localize('Command palette')"
        @cancel="onDialogCancel"
        @click="onClickDialog"
        @close="onDialogClose"
        @mousedown="onDialogMousedown">
        <div class="palette-input">
            <FontAwesomeIcon class="palette-input-icon" fixed-width :icon="inputIcon" :spin="searching" />

            <button
                v-if="badgeText"
                class="palette-badge"
                type="button"
                data-description="palette badge"
                :aria-label="badgeAriaLabel"
                @click="dismissBadge">
                {{ badgeText }}

                <FontAwesomeIcon :icon="faTimes" />
            </button>

            <input
                ref="inputElement"
                data-description="palette input"
                type="text"
                role="combobox"
                autocomplete="off"
                spellcheck="false"
                aria-haspopup="listbox"
                :aria-label="localize('Search Galaxy')"
                aria-expanded="true"
                :placeholder="placeholder"
                :value="text"
                :aria-controls="listboxId"
                :aria-activedescendant="activeDescendant"
                @input="onInput"
                @keydown="onKeydown" />
        </div>

        <!-- Focus stays in the combobox input; the row is driven by ↑↓←→ -->
        <div
            v-if="showCategoryRow"
            ref="categoriesElement"
            class="palette-categories"
            :class="{ 'fade-end': fadeEnd, 'fade-start': fadeStart, 'row-selected': categoryRowSelected }"
            role="tablist"
            :aria-label="localize('Result categories')"
            data-description="palette categories">
            <button
                v-for="category in paletteCategories"
                :key="category.id"
                class="palette-category"
                :class="{ active: category.id === activeCategoryId }"
                type="button"
                role="tab"
                tabindex="-1"
                :aria-selected="category.id === activeCategoryId ? 'true' : 'false'"
                :data-description="`palette category ${category.id}`"
                @click="onCategoryClick(category)">
                {{ localize(category.label) }}
            </button>
        </div>

        <div
            :id="listboxId"
            ref="resultsElement"
            class="palette-results"
            role="listbox"
            :aria-label="localize('Search results')">
            <div
                v-for="(section, sectionIdx) in visibleSections"
                :key="section.id"
                role="group"
                :aria-label="localize(section.title)"
                :data-description="`palette section ${section.id}`">
                <div class="palette-section-title" aria-hidden="true">{{ localize(section.title) }}</div>

                <!-- Nothing rendered and nothing answered yet, so the section holds its place -->
                <template v-if="section.loading && section.items.length === 0">
                    <div
                        v-for="row in SKELETON_ROWS"
                        :key="row"
                        class="palette-skeleton"
                        aria-hidden="true"
                        data-description="palette skeleton">
                        <span class="skeleton-bar skeleton-title"></span>

                        <span class="skeleton-bar skeleton-subtitle"></span>
                    </div>
                </template>

                <template v-else>
                    <CommandPaletteItem
                        v-for="(item, itemIdx) in section.items"
                        :id="optionId(optionIndex(sectionIdx, itemIdx))"
                        :key="item.id"
                        :active="optionIndex(sectionIdx, itemIdx) === selectedIndex"
                        :item="item"
                        :secondary-hint="secondaryHint(optionIndex(sectionIdx, itemIdx), item)"
                        :show-external="showExternalIcon(optionIndex(sectionIdx, itemIdx), item)"
                        @select="runItem(item, $event)"
                        @highlight="highlightItem(optionIndex(sectionIdx, itemIdx))" />
                </template>
            </div>

            <div v-if="scopeHint" class="palette-hint" data-description="palette scope hint">
                {{ scopeHint }}
            </div>

            <div v-else-if="errorHint" class="palette-hint" data-description="palette error">
                {{ errorHint }}
            </div>

            <!-- A section still loading speaks for itself, so the hints only stand in for nothing at all -->
            <div
                v-else-if="visibleSections.length === 0 && argumentHint"
                class="palette-hint"
                data-description="palette argument hint">
                {{ argumentHint }}
            </div>

            <div
                v-else-if="visibleSections.length === 0 && searching"
                class="palette-hint"
                data-description="palette searching">
                {{ localize("Searching…") }}
            </div>

            <div v-else-if="visibleSections.length === 0" class="palette-hint" data-description="palette empty">
                {{ localize("No results.") }}
            </div>
        </div>

        <div class="palette-footer">
            <span
                v-for="hint in footerHints"
                :key="hint.id"
                :class="{
                    'hint-active': hint.active,
                    'hint-right': hint.id === 'help',
                    'hint-optional': OPTIONAL_HINTS.includes(hint.id),
                }"
                :data-description="`palette hint ${hint.id}`">
                <kbd>{{ hint.keys }}</kbd>

                {{ hint.label }}
            </span>
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

    // a short viewport has no room for the drop, so the dialog rides near the top
    @media (max-height: 40rem) {
        margin-top: var(--spacing-3);
    }

    // a phone-width viewport gives the dialog everything but a thin gutter
    @media (max-width: 30rem) {
        width: calc(100vw - var(--spacing-3));
        border-radius: var(--spacing-1);
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

    .palette-categories {
        display: flex;
        align-items: center;
        gap: var(--spacing-1);
        padding: var(--spacing-2) var(--spacing-3);
        border-bottom: 1px solid var(--color-grey-200);
        overflow-x: auto;
        // scrollable without a scrollbar; the faded edges show there is more
        scrollbar-width: none;
        // keeps chips revealed by the arrow keys clear of the fade
        scroll-padding-inline: var(--palette-fade-width);
        --palette-fade-width: 2rem;
        --palette-fade-start: 0;
        --palette-fade-end: 0;
        // a mask fades whatever sits beneath, so it needs no theme colors
        mask-image: linear-gradient(
            to right,
            transparent,
            #000 calc(var(--palette-fade-start) * var(--palette-fade-width)),
            #000 calc(100% - var(--palette-fade-end) * var(--palette-fade-width)),
            transparent
        );

        &::-webkit-scrollbar {
            display: none;
        }

        &.fade-start {
            --palette-fade-start: 1;
        }

        &.fade-end {
            --palette-fade-end: 1;
        }

        .palette-category {
            flex: none;
            padding: 0 var(--spacing-2);
            border: 1px solid transparent;
            border-radius: var(--spacing-2);
            background: none;
            color: var(--color-grey-600);
            font-size: var(--font-size-small);
            white-space: nowrap;

            &.active {
                border-color: var(--color-blue-300);
                background-color: var(--color-blue-100);
                color: var(--color-blue-800);
                font-weight: 600;
            }
        }

        // the row is one stop of the arrow key traversal, so it shows whether
        // the next ←→ would move the category or the caret
        &.row-selected .palette-category.active {
            box-shadow: 0 0 0 2px var(--color-blue-600);
        }
    }

    .palette-results {
        // fixed rather than capped, so the dialog keeps one height across every
        // result set, the help mode and the empty states — until the viewport is
        // too short for it, where the 14rem reserve keeps input and footer on screen
        height: min(21rem, calc(100vh - 14rem));
        height: min(21rem, calc(100dvh - 14rem));
        display: flex;
        flex-direction: column;
        overflow-y: auto;
        padding-bottom: var(--spacing-1);

        // sections keep their natural height; only the hint takes the slack
        > * {
            flex: none;
        }

        .palette-section-title {
            font-size: var(--font-size-small);
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--color-grey-500);
            padding: var(--spacing-2) var(--spacing-3) var(--spacing-1);
        }

        // stands in for a row of a provider that has not answered yet, laid out
        // like the title and subtitle it will be replaced by
        .palette-skeleton {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-1);
            padding: var(--spacing-2) var(--spacing-3);

            .skeleton-bar {
                height: 0.55rem;
                border-radius: var(--spacing);
                background-image: linear-gradient(
                    90deg,
                    var(--color-grey-200) 25%,
                    var(--color-grey-100) 37%,
                    var(--color-grey-200) 63%
                );
                background-size: 400% 100%;
                animation: palette-skeleton-shimmer 1.4s ease infinite;
            }

            .skeleton-title {
                width: 40%;
            }

            .skeleton-subtitle {
                width: 25%;
            }

            @media (prefers-reduced-motion: reduce) {
                .skeleton-bar {
                    animation: none;
                }
            }
        }

        .palette-hint {
            // centered in whatever is left, so a lone hint sits mid-dialog
            margin: auto;
            padding: var(--spacing-3);
            text-align: center;
            color: var(--color-grey-600);
        }
    }

    .palette-footer {
        display: flex;
        // the hint list grows with the mode, so it wraps rather than overflows
        flex-wrap: wrap;
        gap: var(--spacing-3);
        row-gap: var(--spacing-1);
        padding: var(--spacing-1) var(--spacing-3);
        background-color: var(--color-grey-100);
        border-top: 1px solid var(--color-grey-200);
        color: var(--color-grey-600);
        font-size: var(--font-size-small);

        span {
            display: inline-flex;
            align-items: center;
            gap: var(--spacing-1);
            white-space: nowrap;
        }

        // help is the odd one out: it sits opposite the bindings it explains
        .hint-right {
            margin-left: auto;
        }

        // a narrow footer keeps only what runs an item or leaves the palette
        @media (max-width: 30rem) {
            .hint-optional {
                display: none;
            }
        }

        kbd {
            background-color: var(--background-color);
            border: 1px solid var(--color-grey-300);
            border-radius: var(--spacing);
            color: var(--color-grey-600);
            // the ↑↓ ⇧↵ ⌫ glyphs are missing from the monospace default on some platforms
            font-family: inherit;
            font-size: inherit;
            line-height: 1.4;
            padding: 0 var(--spacing-1);
        }

        // the binding the next enter would trigger, swapped while ctrl/cmd is held
        .hint-active {
            color: var(--color-blue-800);
            font-weight: bold;

            kbd {
                border-color: var(--color-blue-300);
                background-color: var(--color-blue-100);
                color: var(--color-blue-800);
            }
        }
    }
}

@keyframes palette-skeleton-shimmer {
    from {
        background-position: 100% 50%;
    }

    to {
        background-position: 0 50%;
    }
}
</style>
