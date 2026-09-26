import { computed, type Ref } from "vue";

import { localize } from "@/utils/localization";

import type { PaletteItem } from "./types";
import type { PaletteMode } from "./usePaletteMachine";

/** Leading phrase of the root placeholder, unless the instance configures its own */
const ROOT_PLACEHOLDER_PHRASE = "Search Galaxy";
/** Key hints trailing whichever leading phrase the root placeholder uses */
const ROOT_PLACEHOLDER_HINT = "…  > actions · w: t: … scopes · ? help";
const HELP_PLACEHOLDER = "Search shortcuts…";

/** Hints a narrow footer drops first, keeping the bindings that run something or leave the palette */
export const OPTIONAL_HINTS = ["navigate", "category", "remove-scope", "remove-action"];

/** One key hint rendered in the footer, driven by the current palette mode */
export interface FooterHint {
    /** Emphasized hint — the binding the next `↵` would trigger */
    active?: boolean;
    id: string;
    keys: string;
    label: string;
}

interface PaletteFooterOptions {
    categoryRowSelected: Readonly<Ref<boolean>>;
    mode: Readonly<Ref<PaletteMode>>;
    modifierHeld: Readonly<Ref<boolean>>;
    /** The platform's "⌘" or "Ctrl+" */
    modifierLabel: Readonly<Ref<string>>;
    /** Instance-configured leading phrase of the root placeholder */
    placeholderPhrase: Readonly<Ref<string | undefined>>;
    selectedItem: Readonly<Ref<PaletteItem | undefined>>;
    shiftHeld: Readonly<Ref<boolean>>;
    showCategoryRow: Readonly<Ref<boolean>>;
    text: Readonly<Ref<string>>;
}

/** What `⇧↵` would do with one item, unset when the item offers nothing */
export function secondaryLabelFor(item: PaletteItem | undefined) {
    if (item?.argumentMode) {
        return localize(item.argumentMode.label ?? "options");
    }
    return item?.secondaryAction ? localize(item.secondaryAction.label) : undefined;
}

function searchLabel(subject: string) {
    return `${localize("Search")} ${subject.toLowerCase()}…`;
}

/** The input placeholder and the footer's key hints, both following the palette mode */
export function usePaletteFooter(options: PaletteFooterOptions) {
    const {
        categoryRowSelected,
        mode,
        modifierHeld,
        modifierLabel,
        placeholderPhrase,
        selectedItem,
        shiftHeld,
        showCategoryRow,
        text,
    } = options;

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
        // an instance-configured phrase is admin copy, so it is used verbatim
        const phrase = placeholderPhrase.value || localize(ROOT_PLACEHOLDER_PHRASE);
        return `${phrase}${localize(ROOT_PLACEHOLDER_HINT)}`;
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
    const secondaryLabel = computed(() => secondaryLabelFor(selectedItem.value));

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
            // shift takes the enter before ctrl/cmd ever sees it, so it dims both
            hints.push({
                active: !modifierHeld.value && !shiftHeld.value,
                id: "open",
                keys: "↵",
                label: localize("open"),
            });
            hints.push({
                active: modifierHeld.value && !shiftHeld.value,
                id: "new-tab",
                keys: `${modifierLabel.value}↵`,
                label: localize("new tab"),
            });
        }

        if (secondaryLabel.value) {
            hints.push({ active: shiftHeld.value, id: "secondary", keys: "⇧↵", label: secondaryLabel.value });
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

    return { footerHints, placeholder };
}
