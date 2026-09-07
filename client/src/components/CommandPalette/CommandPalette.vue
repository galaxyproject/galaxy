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
import { watchDebounced, watchImmediate } from "@vueuse/core";
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

import { helpSections } from "./paletteHelp";
import { enabledPaletteProviders, findPaletteProvider } from "./providers";
import { ALL_CATEGORY, availableCategories, categoryProviderId, type PaletteCategory } from "./providers/categories";
import { isPaletteFetchError } from "./providers/errors";
import { isProviderEnabled, isScopeLoginGated, type ScopeDefinition } from "./providers/scopes";
import type { CommandPaletteProvider, PaletteContext, PaletteItem, ResultSection } from "./types";
import { usePaletteDialog } from "./usePaletteDialog";
import { OPTIONAL_HINTS, secondaryLabelFor, usePaletteFooter } from "./usePaletteFooter";
import { type PaletteMode, usePaletteMachine } from "./usePaletteMachine";
import { usePaletteModifiers } from "./usePaletteModifiers";
import { useScrollEdges } from "./useScrollEdges";
import { BACKEND_RANKED_SCORE, parsePaletteQuery, scorePaletteItems } from "./utilities";

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

const searching = ref(false);
const sections = ref<ResultSection[]>([]);
const selectedIndex = ref(0);
/**
 * Whether the user placed the selection themselves since this search started.
 * An untouched selection belongs to the results and rides on the first row,
 * best match included; one the user put somewhere follows its own row instead,
 * even back on the first one — see {@link assignSections}.
 */
let selectionTouched = false;
const { modifierHeld, modifierLabel, releaseModifiers, shiftHeld } = usePaletteModifiers(togglePalette);
/** Scope whose provider has not landed yet; renders the temporary hint row */
const pendingScope = ref<ScopeDefinition | null>(null);
/** What the palette could not load, naming the scope in the error row */
const failedSubject = ref<string | null>(null);

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

/**
 * Sections worth a heading: one still loading holds its place with skeletons, one
 * that answered with nothing is dropped the moment it does — a bare title over no
 * rows is worse than the gap it leaves. The login offer leads where there is one,
 * over whatever the literal text still finds underneath it.
 */
const visibleSections = computed(() => {
    const answered = sections.value.filter((section) => section.loading || section.items.length > 0);
    return loginPromptSection.value ? [loginPromptSection.value, ...answered] : answered;
});

const flatItems = computed(() => visibleSections.value.flatMap((section) => section.items));

const selectedItem = computed(() => flatItems.value[selectedIndex.value]);

const activeDescendant = computed(() => (selectedItem.value ? optionId(selectedIndex.value) : undefined));

const paletteCategories = computed(() => availableCategories(buildContext()));

/** The row only narrows an unscoped search, so it needs a query to narrow */
const showCategoryRow = computed(() => mode.value.type === "root" && query.value !== "");

/** Whether the arrow keys currently move the category instead of the selection */
const categoryRowSelected = computed(() => showCategoryRow.value && selectedIndex.value === CATEGORY_ROW_INDEX);

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

/** What the current search is *of*, as the error row would name it */
function searchSubject(activeMode: PaletteMode): string {
    if (activeMode.type === "scoped") {
        return localize(activeMode.scope.label).toLowerCase();
    }
    if (activeMode.type === "action") {
        return localize(activeMode.action.title).toLowerCase();
    }
    const category = activeCategory.value;
    return category ? localize(category.label).toLowerCase() : localize("the results");
}

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

/** One provider failing must never cost the user every other section */
function withoutFailing<T>(providerId: string, run: () => T | Promise<T>, fallback: T): Promise<T> {
    return Promise.resolve()
        .then(run)
        .catch((error) => {
            if (isPaletteFetchError(error)) {
                // a scope that could not be loaded at all says so, rather than
                // rendering as an empty one — see `runSearch`
                throw error;
            }
            console.debug(`Command palette provider "${providerId}" failed`, error);
            return fallback;
        });
}

async function providerItems(providerId: string, ctx: PaletteContext): Promise<PaletteItem[]> {
    const provider = findPaletteProvider(providerId);
    // a remembered category or scope must not reach a provider turned off since
    if (!provider || !isProviderEnabled(providerId, ctx)) {
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

/**
 * How well a provider answered, deciding where its section ends up.
 *
 * @param searched the query the items were fetched for, which the input may have
 * moved on from while the provider was answering
 */
function sectionScore(provider: CommandPaletteProvider, items: PaletteItem[], searched: string): number {
    if (!searched) {
        return 0;
    }
    return provider.id === "tools"
        ? BACKEND_RANKED_SCORE
        : Math.max(0, ...scorePaletteItems(items, searched).map((match) => match.order));
}

/**
 * Renders a new set of sections without losing the selected row: a selection the
 * user moved off the top follows its item wherever the new set puts it, and one
 * that is gone falls back to the first row. A rerun the category row started
 * keeps the selection on the row, so the next ←→ moves on to its neighbor.
 *
 * @param followTopRow whether a selection still sitting on the first row follows
 * its item too. Reordering rows already on screen asks for it once the user
 * placed that selection — the fan-out's closing sort must not swap the row they
 * pointed at — while an untouched one belongs to the results and stays on the
 * best match the sort brings to the top.
 */
function assignSections(next: ResultSection[], keepCategoryRow: boolean, followTopRow = false) {
    // the top of the list is where every search starts and where it stays, so
    // outside a reorder only a selection moved away from it is worth following
    const selectedId = followTopRow || selectedIndex.value > 0 ? selectedItem.value?.id : undefined;
    sections.value = next;
    if (keepCategoryRow && showCategoryRow.value) {
        selectedIndex.value = CATEGORY_ROW_INDEX;
        return;
    }
    const index = selectedId ? flatItems.value.findIndex((item) => item.id === selectedId) : -1;
    selectedIndex.value = index >= 0 ? index : 0;
}

/**
 * Unscoped search: every provider contributes a section, rendered the moment it
 * answers rather than once the slowest one has — until then the rows it answered
 * the previous keystroke with hold its place, and a placeholder does where there
 * are none. The sections keep the registry order while the results arrive and
 * are sorted best match first exactly once, when the last provider settled; a
 * selection the user placed follows its row through that sort, so no row is
 * pulled out from under the cursor mid-search.
 */
function fanOutIncrementally(ctx: PaletteContext, epoch: number, keepCategoryRow: boolean) {
    // what this fan-out is answering; the input may have moved on by the time a
    // provider lands, and its rows are still the results of this query
    const searched = query.value;
    const limit = searched ? MAX_ROOT_SECTION_ITEMS : MAX_EMPTY_QUERY_ITEMS;
    const providers = enabledPaletteProviders(ctx);
    let pending = providers.length;
    // a keystroke is not a new search subject: whatever a provider answered the
    // previous one with keeps rendering until it answers this one, so a search
    // that now reaches the backend does not blank the results on every letter
    const rendered = new Map(sections.value.map((section) => [section.id, section.items]));
    assignSections(
        providers.map((provider) => ({
            id: provider.id,
            items: rendered.get(provider.id) ?? [],
            loading: true,
            title: provider.title,
        })),
        keepCategoryRow,
    );
    if (pending === 0) {
        // an instance may turn every provider off, and nothing would land to
        // stop the spinner then
        searching.value = false;
        return;
    }
    providers.forEach((provider) => {
        providerItems(provider.id, ctx)
            // root mode is not local for every provider — tools, and the
            // listing searches of histories, workflows and pages, do reach the
            // backend — so a rejection is ordinary here: it costs its own
            // section rather than the spinner it would leave running
            .catch(() => [] as PaletteItem[])
            .then((items) => {
                if (epoch !== searchEpoch) {
                    // a newer search owns the results now, these are dropped whole
                    return;
                }
                const landed: ResultSection = {
                    id: provider.id,
                    items: items.slice(0, limit),
                    score: sectionScore(provider, items, searched),
                    title: provider.title,
                };
                // a fresh array every time — Vue 2 never sees a section replaced
                // in place
                assignSections(
                    sections.value.map((section) => (section.id === provider.id ? landed : section)),
                    keepCategoryRow,
                );
                pending--;
                if (pending === 0) {
                    assignSections(
                        sections.value
                            .filter((section) => section.items.length > 0)
                            .sort((a, b) => (b.score ?? 0) - (a.score ?? 0)),
                        keepCategoryRow,
                        // the sort moves rows the user may already be pointing
                        // at, the first one included, so a selection they placed
                        // follows its item rather than the position it sat at
                        selectionTouched,
                    );
                    searching.value = false;
                }
            });
    });
}

/**
 * Root mode once the category row narrowed it to a single provider, searched
 * through that provider's own scope. Unscoped "All" never reaches here — it
 * renders provider by provider, see {@link fanOutIncrementally}.
 */
async function rootSections(ctx: PaletteContext): Promise<ResultSection[]> {
    const category = activeCategory.value;
    if (!category) {
        return [];
    }
    return limitSections(await categorySections(category, ctx), MAX_CATEGORY_SECTION_ITEMS);
}

/**
 * A category is a soft scope: the provider's own scoped search runs it where
 * there is one, everything else falls back to its unscoped — and therefore
 * cache-only — root search.
 */
async function categorySections(category: PaletteCategory, ctx: PaletteContext): Promise<ResultSection[]> {
    const providerId = categoryProviderId(category);
    const provider = providerId ? findPaletteProvider(providerId) : undefined;
    if (!provider || !isProviderEnabled(provider.id, ctx)) {
        return [];
    }
    return providerSections(provider, category.scope, ctx);
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
    if (provider && !isProviderEnabled(provider.id, ctx)) {
        return [];
    }
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
            return helpSections(ctx, query.value, modifierLabel.value, { enterScope, popMode, setText });
        case "action":
            return actionSections(activeMode.action, ctx);
        case "scoped":
            return scopedSections(activeMode.scope, ctx);
        default:
            return rootSections(ctx);
    }
}

let searchEpoch = 0;

/** Badge or category the results belong to; any change but the query invalidates them */
function searchIdentity(activeMode: PaletteMode): string {
    switch (activeMode.type) {
        case "scoped":
            return `scoped:${activeMode.scope.key}`;
        case "action":
            return `action:${activeMode.action.id}`;
        case "help":
            return "help";
        default:
            return `root:${activeMode.category?.id ?? ALL_CATEGORY.id}`;
    }
}

/** Drops the rendered results and any search still in flight for them */
function clearResults() {
    searchEpoch++;
    sections.value = [];
    selectedIndex.value = 0;
    pendingScope.value = null;
    failedSubject.value = null;
    searching.value = true;
}

async function runSearch() {
    const epoch = ++searchEpoch;
    const ctx = buildContext();
    // picking a category reruns the search; the row keeps the selection so the
    // next ←→ moves on to the neighboring category
    const keepCategoryRow = categoryRowSelected.value;
    // typing is about the results again, so the selection is the search's until
    // the user places it somewhere themselves
    selectionTouched = false;
    pendingScope.value = null;
    failedSubject.value = null;
    searching.value = true;
    if (mode.value.type === "root" && !activeCategory.value) {
        // the fan-out renders every provider as it answers, so it owns the
        // sections, the selection and the spinner from here on
        fanOutIncrementally(ctx, epoch, keepCategoryRow);
        return;
    }
    try {
        const results = await modeSections(mode.value, ctx);
        if (epoch === searchEpoch) {
            sections.value = results.filter((section) => section.items.length > 0);
            selectedIndex.value = keepCategoryRow && showCategoryRow.value ? CATEGORY_ROW_INDEX : 0;
        }
    } catch (error) {
        // only a scope that could not be loaded at all reaches this, everything
        // else is degraded to an empty section by `withoutFailing`
        console.debug("Command palette could not load the current scope", error);
        if (epoch === searchEpoch) {
            sections.value = [];
            selectedIndex.value = 0;
            failedSubject.value = searchSubject(mode.value);
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
 * Vertical traversal. The category row rides along as one more stop above the
 * first result, so ↑ from it — or wrapping past the last item — selects it.
 */
function moveSelection(delta: 1 | -1) {
    selectionTouched = true;
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

/** Hovering a row selects it, which is the user placing the selection as well */
function highlightItem(index: number) {
    selectionTouched = true;
    selectedIndex.value = index;
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

// sync so old rows never show under a new badge; reads `mode` as a sync watcher can see a stale computed
watch(() => searchIdentity(mode.value), clearResults, { flush: "sync" });

// the category is part of the mode, so a sweep across the row shares the debounce
watchDebounced([text, mode], runSearch, { debounce: SEARCH_DEBOUNCE });

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
