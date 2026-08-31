<script setup lang="ts">
import { faSearch, faSpinner, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventListener, watchDebounced, watchImmediate } from "@vueuse/core";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { useStartNewChat } from "@/components/GalaxyAI/useStartNewChat";
import { useFilteredUploadMethods } from "@/components/Panels/Upload/uploadMethodRegistry";
import { useConfig } from "@/composables/config";
import { useCommandPalette } from "@/composables/useCommandPalette";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { useUid } from "@/composables/utils/uid";
import { useEventStore } from "@/stores/eventStore";
import { useToolStore } from "@/stores/toolStore";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { useUserStore } from "@/stores/userStore";
import { localize } from "@/utils/localization";

import { findPaletteProvider, paletteProviders, rankPaletteItems } from "./providers";
import { ALL_CATEGORY, availableCategories, categoryScope, type PaletteCategory } from "./providers/categories";
import { ACTIONS_SCOPE, availableScopes, type ScopeDefinition } from "./providers/scopes";
import type { CommandPaletteProvider, PaletteContext, PaletteItem } from "./types";
import { type PaletteMode, usePaletteMachine } from "./usePaletteMachine";
import { scorePaletteItems } from "./utilities";

import CommandPaletteItem from "./CommandPaletteItem.vue";

const SEARCH_DEBOUNCE = 150;
/** Cap per section on an empty query so defaults stay scannable */
const MAX_EMPTY_QUERY_ITEMS = 8;
/** Cap per section of the "All" fan-out, so every provider stays visible */
const MAX_ROOT_SECTION_ITEMS = 5;
/** Cap per section once a single category narrows the results */
const MAX_CATEGORY_SECTION_ITEMS = 15;
/** `selectedIndex` value selecting the category row instead of a result */
const CATEGORY_ROW_INDEX = -1;
/** Safety net for environments that never fire `transitionend` (jsdom, backgrounded tabs) */
const CLOSE_TRANSITION_FALLBACK = 200;

const ROOT_PLACEHOLDER = "Search Galaxy…  > actions · w: t: … scopes · ? help";
const HELP_PLACEHOLDER = "Search shortcuts…";

interface ResultSection {
    id: string;
    items: PaletteItem[];
    title: string;
}

/** One key hint rendered in the footer, driven by the current palette mode */
interface FooterHint {
    /** Emphasized hint — the binding the next `↵` would trigger */
    active?: boolean;
    id: string;
    keys: string;
    label: string;
}

const { isPaletteOpen, closePalette, togglePalette } = useCommandPalette();
const { addRecentItem } = useRecentPaletteItems();
// these composables need a component instance, so the palette resolves them once
// and hands them to the providers through the context
const uploadMethods = useFilteredUploadMethods();
const startNewChat = useStartNewChat();
const router = useRouter();
const { config } = useConfig();
const eventStore = useEventStore();
const toolStore = useToolStore();
const unprivilegedToolStore = useUnprivilegedToolStore();
const userStore = useUserStore();

// the machine needs the context to reject scope tokens the user may not use;
// `buildContext` is a hoisted declaration, so it is safe to hand over here
const { badgeLabel, enterAction, enterScope, handleEscape, mode, popMode, query, reset, setText, text } =
    usePaletteMachine(buildContext);

const dialogElement = ref<HTMLDialogElement | null>(null);
const inputElement = ref<HTMLInputElement | null>(null);
const searching = ref(false);
const sections = ref<ResultSection[]>([]);
const selectedIndex = ref(0);
/** Category the root results are narrowed to, "All" while nothing is picked */
const activeCategoryId = ref(ALL_CATEGORY.id);
/** Whether ctrl/cmd is currently down, so the palette can preview "new tab" */
const modifierHeld = ref(false);
/** Scope whose provider has not landed yet; renders the temporary hint row */
const pendingScope = ref<ScopeDefinition | null>(null);

const uid = useUid("command-palette");
const listboxId = computed(() => `${uid.value}-listbox`);

const flatItems = computed(() => sections.value.flatMap((section) => section.items));

const selectedItem = computed(() => flatItems.value[selectedIndex.value]);

const activeDescendant = computed(() => (selectedItem.value ? optionId(selectedIndex.value) : undefined));

const modifierLabel = computed(() => (eventStore.isMac ? "⌘" : "Ctrl+"));

const paletteCategories = computed(() => availableCategories(buildContext()));

/** The row only narrows an unscoped search, so it needs a query to narrow */
const showCategoryRow = computed(() => mode.value.type === "root" && query.value !== "");

/** Whether the arrow keys currently move the category instead of the selection */
const categoryRowSelected = computed(() => showCategoryRow.value && selectedIndex.value === CATEGORY_ROW_INDEX);

/** Category narrowing the results, unset while "All" is active or hidden */
const activeCategory = computed(() => {
    if (!showCategoryRow.value) {
        return undefined;
    }
    const category = paletteCategories.value.find((entry) => entry.id === activeCategoryId.value);
    return category?.providerId ? category : undefined;
});

/** Badge text, localized here because the providers keep their strings in English */
const badgeText = computed(() => (badgeLabel.value ? localize(badgeLabel.value) : undefined));

const badgeAriaLabel = computed(() => `${localize("Remove filter")}: ${badgeText.value}`);

const placeholder = computed(() => {
    const activeMode = mode.value;
    if (activeMode.type === "action") {
        const argumentMode = activeMode.action.argumentMode;
        return argumentMode ? localize(argumentMode.placeholder) : searchLabel(localize(activeMode.action.title));
    }
    if (activeMode.type === "scoped") {
        return searchLabel(localize(activeMode.scope.label));
    }
    if (activeMode.type === "help") {
        return localize(HELP_PLACEHOLDER);
    }
    return localize(ROOT_PLACEHOLDER);
});

/** Escape steps through clearing the text, then the badge, then closing */
const escapeLabel = computed(() => {
    if (text.value !== "") {
        return localize("clear");
    }
    if (mode.value.type !== "root") {
        return localize("back");
    }
    return localize("close");
});

/** What `⇧↵` would do with the selected item, unset when it offers nothing */
const secondaryLabel = computed(() => {
    const item = selectedItem.value;
    if (item?.argumentMode) {
        return localize(item.argumentMode.label ?? "options");
    }
    return item?.secondaryAction ? localize(item.secondaryAction.label) : undefined;
});

const footerHints = computed<FooterHint[]>(() => {
    const activeMode = mode.value;
    const hints: FooterHint[] = [{ id: "navigate", keys: "↑↓", label: localize("navigate") }];

    if (showCategoryRow.value) {
        hints.push({
            active: categoryRowSelected.value,
            id: "category",
            keys: "←→",
            label: localize("category"),
        });
    }
    if (activeMode.type === "action") {
        hints.push({ id: "run", keys: "↵", label: localize("run") });
    } else if (activeMode.type === "help") {
        hints.push({ id: "apply", keys: "↵", label: localize("apply") });
    } else {
        hints.push({ active: !modifierHeld.value, id: "open", keys: "↵", label: localize("open") });
        hints.push({
            active: modifierHeld.value,
            id: "new-tab",
            keys: `${modifierLabel.value}↵`,
            label: localize("new tab"),
        });
    }

    if (secondaryLabel.value) {
        hints.push({ id: "secondary", keys: "⇧↵", label: secondaryLabel.value });
    }
    if (activeMode.type === "scoped") {
        hints.push({ id: "remove-scope", keys: "⌫", label: localize("remove filter") });
    } else if (activeMode.type === "action") {
        hints.push({ id: "remove-action", keys: "⌫", label: localize("remove filter") });
    }

    hints.push({ id: "escape", keys: "esc", label: escapeLabel.value });
    if (activeMode.type === "root") {
        hints.push({ id: "help", keys: "?", label: localize("help") });
    }
    return hints;
});

const scopeHint = computed(() => {
    const scope = pendingScope.value;
    if (!scope) {
        return undefined;
    }
    return `${localize(scope.label)} — ${localize("this filter has no results provider yet.")}`;
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
            enable_notification_system: config.value?.enable_notification_system,
            interactivetools_enable: config.value?.interactivetools_enable,
            llm_api_configured: config.value?.llm_api_configured,
        },
        isAdmin: userStore.isAdmin,
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

/** A key binding row: the description reads as the title, the keys as the badge */
function helpKeyItem(id: string, keys: string, title: string, keywords: string): PaletteItem {
    return { id: `help:key:${id}`, keywords, shortcut: keys, title: localize(title) };
}

/** The bindings the palette answers to, documented in the help panel */
function helpKeyItems(): PaletteItem[] {
    return [
        helpKeyItem("open", "↵", "Open the selected result", "enter return open run"),
        helpKeyItem("secondary", "⇧↵", "Secondary action, or the options of an action", "shift enter options argument"),
        helpKeyItem(
            "new-tab",
            `${modifierLabel.value}↵`,
            "Open in a new tab, keeping the palette open",
            "command control meta enter tab window",
        ),
        helpKeyItem("navigate", "↑↓", "Move through the results", "arrow up down navigate select"),
        helpKeyItem("category", "←→", "Move between categories, once the category row is selected", "arrow left right"),
        helpKeyItem("remove", "⌫", "Remove the active filter", "backspace delete scope action badge"),
        helpKeyItem("escape", "esc", "Clear the text, then the filter, then close", "escape back close clear"),
    ];
}

function helpSections(ctx: PaletteContext): ResultSection[] {
    return [
        { id: "help:actions", items: [scopeHelpItem(ACTIONS_SCOPE)], title: "Actions" },
        { id: "help:scopes", items: availableScopes(ctx).map(scopeHelpItem), title: "Scopes" },
        { id: "help:keys", items: helpKeyItems(), title: "Keys" },
    ].map((section) => ({ ...section, items: rankPaletteItems(section.items, query.value) }));
}

/** One provider failing must never cost the user every other section */
function withoutFailing<T>(providerId: string, run: () => T | Promise<T>, fallback: T): Promise<T> {
    return Promise.resolve()
        .then(run)
        .catch((error) => {
            console.debug(`Command palette provider "${providerId}" failed`, error);
            return fallback;
        });
}

async function providerItems(providerId: string, ctx: PaletteContext): Promise<PaletteItem[]> {
    const provider = findPaletteProvider(providerId);
    if (!provider) {
        return [];
    }
    return withoutFailing(
        providerId,
        () =>
            !query.value && provider.emptyQueryItems
                ? provider.emptyQueryItems(ctx).slice(0, MAX_EMPTY_QUERY_ITEMS)
                : provider.search(query.value, ctx),
        [],
    );
}

function limitSections(list: ResultSection[], limit: number): ResultSection[] {
    return list.map((section) =>
        section.items.length > limit ? { ...section, items: section.items.slice(0, limit) } : section,
    );
}

/** Unscoped search: every provider contributes a section, best match first */
async function fanOutSections(ctx: PaletteContext): Promise<ResultSection[]> {
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

/**
 * Root mode: the fan-out over every provider, or — once the category row picked
 * one — that single provider searched through its own scope.
 */
async function rootSections(ctx: PaletteContext): Promise<ResultSection[]> {
    const category = activeCategory.value;
    if (category) {
        return limitSections(await categorySections(category, ctx), MAX_CATEGORY_SECTION_ITEMS);
    }
    const fanOut = await fanOutSections(ctx);
    return query.value ? limitSections(fanOut, MAX_ROOT_SECTION_ITEMS) : fanOut;
}

/**
 * A category is a soft scope: the provider's own scoped search runs it where
 * there is one, everything else falls back to its unscoped — and therefore
 * cache-only — root search.
 */
async function categorySections(category: PaletteCategory, ctx: PaletteContext): Promise<ResultSection[]> {
    const provider = category.providerId ? findPaletteProvider(category.providerId) : undefined;
    if (!provider) {
        return [];
    }
    return providerSections(provider, categoryScope(category), ctx);
}

async function providerSections(
    provider: CommandPaletteProvider,
    scope: ScopeDefinition | undefined,
    ctx: PaletteContext,
): Promise<ResultSection[]> {
    if (scope && provider.searchScoped) {
        const scoped = await withoutFailing(provider.id, () => provider.searchScoped!(scope, query.value, ctx), []);
        return scoped.map((section) => ({ ...section, id: `${provider.id}:${section.id}` }));
    }
    return [{ id: provider.id, items: await providerItems(provider.id, ctx), title: provider.title }];
}

async function scopedSections(scope: ScopeDefinition, ctx: PaletteContext): Promise<ResultSection[]> {
    const provider = findPaletteProvider(scope.providerId);
    // a variant (shared, published, …) can only be served by a scoped search
    if (!provider || (scope.variant && !provider.searchScoped)) {
        pendingScope.value = scope;
        return [];
    }
    return providerSections(provider, scope, ctx);
}

/**
 * Argument mode: the input collects the action's argument and the action itself
 * turns the typed text into the rows to pick from. Free text actions surface the
 * text as their own first item, so enter always runs the selected row.
 */
async function actionSections(action: PaletteItem, ctx: PaletteContext): Promise<ResultSection[]> {
    const argumentMode = action.argumentMode;
    if (!argumentMode) {
        return [];
    }
    const items = await withoutFailing(action.id, () => argumentMode.getItems(query.value, ctx), []);
    return [{ id: `action:${action.id}`, items, title: localize(action.title) }];
}

function modeSections(activeMode: PaletteMode, ctx: PaletteContext): Promise<ResultSection[]> | ResultSection[] {
    switch (activeMode.type) {
        case "help":
            return helpSections(ctx);
        case "action":
            return actionSections(activeMode.action, ctx);
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
    // picking a category reruns the search; the row keeps the selection so the
    // next ←→ moves on to the neighboring category
    const keepCategoryRow = categoryRowSelected.value;
    pendingScope.value = null;
    searching.value = true;
    try {
        const results = await modeSections(mode.value, ctx);
        if (epoch === searchEpoch) {
            sections.value = results.filter((section) => section.items.length > 0);
            selectedIndex.value = keepCategoryRow && showCategoryRow.value ? CATEGORY_ROW_INDEX : 0;
        }
    } finally {
        if (epoch === searchEpoch) {
            searching.value = false;
        }
    }
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
    return modifierHeld.value && index === selectedIndex.value && Boolean(item.to);
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
 * Vertical traversal. The category row rides along as one more stop above the
 * first result, so ↑ from it — or wrapping past the last item — selects it.
 */
function moveSelection(delta: 1 | -1) {
    const count = flatItems.value.length;
    if (!showCategoryRow.value) {
        if (count > 0) {
            selectedIndex.value = (Math.max(selectedIndex.value, 0) + delta + count) % count;
        }
        return;
    }
    const stops = count + 1;
    const position = selectedIndex.value + 1;
    selectedIndex.value = ((position + delta + stops) % stops) - 1;
}

/**
 * Moving onto a category applies it right away, no confirmation needed. The
 * rerun rides the shared debounce, so holding ←→ across the row costs one
 * search instead of one per category passed over.
 */
function selectCategory(categoryId: string) {
    activeCategoryId.value = categoryId;
    selectedIndex.value = CATEGORY_ROW_INDEX;
}

/** The row is keyboard driven, so a clicked chip hands the focus straight back */
function onCategoryClick(categoryId: string) {
    selectCategory(categoryId);
    refocusInput();
}

function moveCategory(delta: 1 | -1) {
    const categories = paletteCategories.value;
    const current = categories.findIndex((category) => category.id === activeCategoryId.value);
    const next = categories[(Math.max(current, 0) + delta + categories.length) % categories.length];
    if (next) {
        selectCategory(next.id);
    }
}

function resetCategory() {
    activeCategoryId.value = ALL_CATEGORY.id;
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

/**
 * The browser's own escape handling closes a modal dialog outright. Escape in
 * the palette is stepwise, so the close request is cancelled and routed through
 * the same handler the input uses — the input's own escape never reaches here,
 * it prevents the keydown default before a close request is even made.
 */
function onDialogCancel(event: Event) {
    event.preventDefault();
    if (handleEscape() === "close") {
        closePalette();
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

// a narrowed search only ever survives the query it was picked for
watch(mode, resetCategory);
watch(showCategoryRow, (visible) => {
    if (!visible) {
        resetCategory();
    }
});

function isNewTabModifier(key: string) {
    return key === "Meta" || key === "Control";
}

useEventListener(window, "keydown", (event: KeyboardEvent) => {
    if (isNewTabModifier(event.key)) {
        modifierHeld.value = true;
    }
    const platformModifier = eventStore.isMac ? event.metaKey : event.ctrlKey;
    if (event.key.toLowerCase() === "k" && platformModifier && !event.shiftKey && !event.altKey && !event.repeat) {
        event.preventDefault();
        togglePalette();
    }
});

useEventListener(window, "keyup", (event: KeyboardEvent) => {
    if (isNewTabModifier(event.key)) {
        modifierHeld.value = false;
    }
});

// opening a new tab moves focus away, so the matching keyup never arrives here
useEventListener(window, "blur", () => {
    modifierHeld.value = false;
});

// the category is part of what is being searched, so it shares the debounce
watchDebounced([text, mode, activeCategoryId], runSearch, { debounce: SEARCH_DEBOUNCE });

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
        resetCategory();
        // hydrate the tool store so recent tools resolve to names
        toolStore.fetchTools()?.catch?.(() => {});
        runSearch();
        openDialog();
    } else {
        modifierHeld.value = false;
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
        @close="onDialogClose">
        <div class="palette-input">
            <FontAwesomeIcon
                class="palette-input-icon"
                fixed-width
                :icon="searching ? faSpinner : faSearch"
                :spin="searching" />

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
            class="palette-categories"
            :class="{ 'row-selected': categoryRowSelected }"
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
                @click="onCategoryClick(category.id)">
                {{ localize(category.label) }}
            </button>
        </div>

        <div :id="listboxId" class="palette-results" role="listbox" :aria-label="localize('Search results')">
            <div
                v-for="(section, sectionIdx) in sections"
                :key="section.id"
                role="group"
                :aria-label="localize(section.title)"
                :data-description="`palette section ${section.id}`">
                <div class="palette-section-title" aria-hidden="true">{{ localize(section.title) }}</div>

                <CommandPaletteItem
                    v-for="(item, itemIdx) in section.items"
                    :id="optionId(optionIndex(sectionIdx, itemIdx))"
                    :key="item.id"
                    :active="optionIndex(sectionIdx, itemIdx) === selectedIndex"
                    :item="item"
                    :show-external="showExternalIcon(optionIndex(sectionIdx, itemIdx), item)"
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
            <span
                v-for="hint in footerHints"
                :key="hint.id"
                :class="{ 'hint-active': hint.active }"
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
</style>
