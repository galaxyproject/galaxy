import { watchDebounced } from "@vueuse/core";
import { computed, type Ref, ref, watch } from "vue";

import { localize } from "@/utils/localization";

import { helpSections, type PaletteHelpHandlers } from "./paletteHelp";
import { enabledPaletteProviders, findPaletteProvider } from "./providers";
import { ALL_CATEGORY, categoryProviderId, type PaletteCategory } from "./providers/categories";
import { isPaletteFetchError } from "./providers/errors";
import { isProviderEnabled, type ScopeDefinition } from "./providers/scopes";
import type { CommandPaletteProvider, PaletteContext, PaletteItem, ResultSection } from "./types";
import type { PaletteMode } from "./usePaletteMachine";
import { BACKEND_RANKED_SCORE, isScopeTokenLike, scorePaletteItems } from "./utilities";

const SEARCH_DEBOUNCE = 150;
/** Cap per section on an empty query so defaults stay scannable */
const MAX_EMPTY_QUERY_ITEMS = 8;
/** Cap per section of the "All" fan-out, so every provider stays visible */
const MAX_ROOT_SECTION_ITEMS = 5;
/** Cap per section once a single category narrows the results */
const MAX_CATEGORY_SECTION_ITEMS = 15;
/** `selectedIndex` value selecting the category row instead of a result */
export const CATEGORY_ROW_INDEX = -1;

interface PaletteSearchOptions {
    /** Category narrowing the root search, unset while "All" is active */
    activeCategory: Readonly<Ref<PaletteCategory | undefined>>;
    buildContext: () => PaletteContext;
    /** What the help rows do to the palette */
    helpHandlers: PaletteHelpHandlers;
    /** Section rendered above whatever the search found, such as the login offer */
    leadingSection: Readonly<Ref<ResultSection | undefined>>;
    mode: Readonly<Ref<PaletteMode>>;
    /** The platform's "⌘" or "Ctrl+" */
    modifierLabel: Readonly<Ref<string>>;
    /** The trimmed text the providers are handed */
    query: Readonly<Ref<string>>;
    /** The input text; every change reruns the search, debounced */
    text: Readonly<Ref<string>>;
}

/**
 * The palette's results: which providers a mode asks, the sections they answer
 * with, and the selection riding on them. Searches rerun on every change of the
 * text or the mode; a change of what is searched clears the rows at once.
 */
export function usePaletteSearch(options: PaletteSearchOptions) {
    const { activeCategory, buildContext, helpHandlers, leadingSection, mode, modifierLabel, query, text } = options;

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
    /** Scope whose provider has not landed yet; renders the temporary hint row */
    const pendingScope = ref<ScopeDefinition | null>(null);
    /** What the palette could not load, naming the scope in the error row */
    const failedSubject = ref<string | null>(null);

    /**
     * Sections worth a heading: one still loading holds its place with skeletons, one
     * that answered with nothing is dropped the moment it does — a bare title over no
     * rows is worse than the gap it leaves. The login offer leads where there is one,
     * over whatever the literal text still finds underneath it.
     */
    const visibleSections = computed(() => {
        const answered = sections.value.filter((section) => section.loading || section.items.length > 0);
        return leadingSection.value ? [leadingSection.value, ...answered] : answered;
    });

    const flatItems = computed(() => visibleSections.value.flatMap((section) => section.items));

    const selectedItem = computed(() => flatItems.value[selectedIndex.value]);

    /** The row only narrows an unscoped search, so it needs a query to narrow */
    const showCategoryRow = computed(() => mode.value.type === "root" && query.value !== "");

    /** Whether the arrow keys currently move the category instead of the selection */
    const categoryRowSelected = computed(() => showCategoryRow.value && selectedIndex.value === CATEGORY_ROW_INDEX);

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
        // an `xy:` still being typed is a filter, not a term for any backend
        const localOnly = isScopeTokenLike(query.value);
        return withoutFailing(
            providerId,
            () =>
                !query.value && provider.emptyQueryItems
                    ? provider.emptyQueryItems(ctx).slice(0, MAX_EMPTY_QUERY_ITEMS)
                    : provider.search(query.value, ctx, { localOnly }),
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
                // listing searches of histories, workflows and reports, do reach
                // the backend — so a rejection is ordinary here: it costs its own
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

    /** Search of the provider a category narrows to, through the category's scope */
    async function categorySections(category: PaletteCategory, ctx: PaletteContext): Promise<ResultSection[]> {
        const providerId = categoryProviderId(category);
        const provider = providerId ? findPaletteProvider(providerId) : undefined;
        if (!provider || !isProviderEnabled(provider.id, ctx)) {
            return [];
        }
        // scoped searches cannot run `localOnly`, so an `xy:` being typed takes the root search
        const scope = isScopeTokenLike(query.value) ? undefined : category.scope;
        return providerSections(provider, scope, ctx);
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
                return helpSections(ctx, query.value, modifierLabel.value, helpHandlers);
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

    // sync so old rows never show under a new badge; reads `mode` as a sync watcher can see a stale computed
    watch(() => searchIdentity(mode.value), clearResults, { flush: "sync" });

    // the category is part of the mode, so a sweep across the row shares the debounce
    watchDebounced([text, mode], runSearch, { debounce: SEARCH_DEBOUNCE });

    return {
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
    };
}
