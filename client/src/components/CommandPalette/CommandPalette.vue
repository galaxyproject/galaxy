<script setup lang="ts">
import { faSearch, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventListener, watchDebounced, watchImmediate } from "@vueuse/core";
import { computed, nextTick, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { useCommandPalette } from "@/composables/useCommandPalette";
import { useUid } from "@/composables/utils/uid";
import { useEventStore } from "@/stores/eventStore";
import { useToolStore } from "@/stores/toolStore";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import { useUserStore } from "@/stores/userStore";

import { paletteProviders, parsePaletteQuery } from "./providers";
import type { PaletteContext, PaletteItem } from "./types";
import { scorePaletteItems } from "./utilities";

import CommandPaletteItem from "./CommandPaletteItem.vue";

const SEARCH_DEBOUNCE = 150;
/** Cap per section on an empty query so defaults stay scannable */
const MAX_EMPTY_QUERY_ITEMS = 8;

const RESERVED_PREFIX_LABELS: Record<string, string> = {
    w: "workflows",
    h: "histories",
    d: "datasets",
    v: "visualizations",
    i: "invocations",
    p: "pages",
};

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

const dialogElement = ref<HTMLDialogElement | null>(null);
const inputElement = ref<HTMLInputElement | null>(null);
const query = ref("");
const reservedPrefix = ref<string | null>(null);
const searching = ref(false);
const sections = ref<ResultSection[]>([]);
const selectedIndex = ref(0);

const uid = useUid("command-palette");
const listboxId = computed(() => `${uid.value}-listbox`);

const flatItems = computed(() => sections.value.flatMap((section) => section.items));

const selectedItem = computed(() => flatItems.value[selectedIndex.value]);

const activeDescendant = computed(() => (selectedItem.value ? optionId(selectedIndex.value) : undefined));

const reservedHint = computed(() => (reservedPrefix.value ? RESERVED_PREFIX_LABELS[reservedPrefix.value] : undefined));

const modifierLabel = computed(() => (eventStore.isMac ? "⌘" : "Ctrl+"));

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

let searchEpoch = 0;

async function runSearch() {
    const epoch = ++searchEpoch;
    const parsed = parsePaletteQuery(query.value);
    reservedPrefix.value = parsed.reservedPrefix ?? null;

    const scopedProviders = parsed.reservedPrefix
        ? []
        : paletteProviders.filter((provider) => !parsed.providerId || provider.id === parsed.providerId);

    const ctx = buildContext();
    searching.value = true;
    try {
        const results = await Promise.all(
            scopedProviders.map(async (provider) => {
                let items: PaletteItem[];
                let score = 0;
                if (!parsed.query && provider.emptyQueryItems) {
                    items = provider.emptyQueryItems(ctx).slice(0, MAX_EMPTY_QUERY_ITEMS);
                } else {
                    items = await provider.search(parsed.query, ctx);
                    // sections are shown best-match first; backend-ranked tools
                    // carry no scores, so they slot between "starts with" (4)
                    // and plain name matches (3) of the local providers
                    score =
                        provider.id === "tools"
                            ? 3.5
                            : Math.max(0, ...scorePaletteItems(items, parsed.query).map((scored) => scored.order));
                }
                return { id: provider.id, items, score, title: provider.title };
            }),
        );
        if (epoch === searchEpoch) {
            sections.value = results.filter((section) => section.items.length > 0).sort((a, b) => b.score - a.score);
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
        case "Enter":
            event.preventDefault();
            runItem(selectedItem.value, event);
            break;
        case "Escape":
            event.preventDefault();
            closePalette();
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

watchDebounced(query, runSearch, { debounce: SEARCH_DEBOUNCE });

watchImmediate(isPaletteOpen, async (open) => {
    if (open) {
        // hydrate the tool store so recent tools resolve to names
        toolStore.fetchTools()?.catch?.(() => {});
        runSearch();
        await nextTick();
        try {
            dialogElement.value?.showModal();
        } catch (e) {
            // dialog may already be open, or the test environment lacks support
        }
        inputElement.value?.focus();
        inputElement.value?.select();
    } else {
        dialogElement.value?.close();
    }
});
</script>

<template>
    <!-- Clicking the backdrop is a mouse-only close shortcut; keyboard users have escape -->
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions, vuejs-accessibility/click-events-have-key-events -->
    <dialog
        ref="dialogElement"
        class="command-palette"
        aria-label="Command palette"
        @click="onClickDialog"
        @close="onDialogClose">
        <div class="palette-input">
            <FontAwesomeIcon
                class="palette-input-icon"
                fixed-width
                :icon="searching ? faSpinner : faSearch"
                :spin="searching" />

            <!-- eslint-disable-next-line vuejs-accessibility/no-autofocus -->
            <input
                ref="inputElement"
                v-model="query"
                data-description="palette input"
                type="text"
                role="combobox"
                autocomplete="off"
                spellcheck="false"
                aria-label="Search Galaxy"
                aria-haspopup="listbox"
                aria-expanded="true"
                placeholder="Search Galaxy…  (> commands, t: tools)"
                :aria-controls="listboxId"
                :aria-activedescendant="activeDescendant"
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

            <div v-if="reservedHint" class="palette-hint" data-description="palette reserved hint">
                <code>{{ reservedPrefix }}:</code> searches {{ reservedHint }} — coming in a future update.
            </div>

            <div v-else-if="flatItems.length === 0 && !searching" class="palette-hint" data-description="palette empty">
                No results.
            </div>
        </div>

        <div class="palette-footer">
            <span><kbd>↑↓</kbd> navigate</span>

            <span><kbd>↵</kbd> open</span>

            <span
                ><kbd>{{ modifierLabel }}↵</kbd> new tab</span
            >

            <span><kbd>esc</kbd> close</span>
        </div>
    </dialog>
</template>

<style scoped lang="scss">
.command-palette {
    width: min(40rem, calc(100vw - 2rem));
    margin-top: 15vh;
    margin-bottom: auto;
    padding: 0;
    border: none;
    border-radius: var(--spacing-2);
    overflow: hidden;
    box-shadow: 0 18px 50px rgba(33, 37, 50, 0.35);

    &::backdrop {
        background-color: var(--color-ebony-clay-950, #212532);
        opacity: 0.45;
    }

    .palette-input {
        display: flex;
        align-items: center;
        gap: var(--spacing-2);
        padding: var(--spacing-3);
        background-color: var(--color-ebony-clay-900, #2c3143);

        .palette-input-icon {
            color: var(--color-gold-500, #ffd700);
        }

        input {
            flex-grow: 1;
            border: none;
            outline: none;
            background: transparent;
            color: var(--color-bay-of-many-100, #edf4fa);

            &::placeholder {
                color: var(--color-ebony-clay-400, var(--color-grey-500));
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
            color: var(--color-ebony-clay-600, var(--color-grey-600));
            padding: var(--spacing-2) var(--spacing-3) var(--spacing-1);
        }

        .palette-hint {
            padding: var(--spacing-3);
            text-align: center;
            color: var(--color-chicago-500, var(--color-grey-600));
        }
    }

    .palette-footer {
        display: flex;
        gap: var(--spacing-3);
        padding: var(--spacing-1) var(--spacing-3);
        background-color: var(--color-ebony-clay-950, #212532);
        color: var(--color-ebony-clay-400, var(--color-grey-400));
        font-size: var(--font-size-small);

        kbd {
            background-color: var(--color-ebony-clay-800, #3c435c);
            border: 1px solid var(--color-ebony-clay-700, #4c5574);
            border-radius: var(--spacing);
            color: var(--color-ebony-clay-100, #d3d6e2);
            font-size: inherit;
            padding: 0 var(--spacing-1);
        }
    }
}
</style>
