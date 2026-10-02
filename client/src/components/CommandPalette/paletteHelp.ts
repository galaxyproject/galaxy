import { localize } from "@/utils/localization";

import { actionsProvider } from "./providers/actions";
import { ACTIONS_SCOPE, availableScopes, type ScopeDefinition } from "./providers/scopes";
import type { PaletteContext, PaletteItem, ResultSection } from "./types";
import { rankPaletteItems } from "./utilities";

/** What the help rows need from the palette to apply the scope or action they document */
export interface PaletteHelpHandlers {
    enterScope: (scope: ScopeDefinition) => void;
    setText: (text: string) => void;
}

/** One help row per scope, selecting it turns the scope into a badge */
export function scopeHelpItem(scope: ScopeDefinition, enterScope: PaletteHelpHandlers["enterScope"]): PaletteItem {
    return {
        id: `help:${scope.key}`,
        handler: () => enterScope(scope),
        keywords: scope.key,
        shortcut: scope.key === ACTIONS_SCOPE.key ? scope.key : `${scope.key}:`,
        title: `${localize("Search")} ${localize(scope.label).toLowerCase()}`,
    };
}

/** A key binding row: the description reads as the title, the keys as the badge */
export function helpKeyItem(id: string, keys: string, title: string, keywords: string): PaletteItem {
    return { id: `help:key:${id}`, keywords, shortcut: keys, title: localize(title) };
}

/** The bindings the palette answers to; `modifierLabel` is the platform's "⌘" or "Ctrl+" */
export function helpKeyItems(modifierLabel: string): PaletteItem[] {
    return [
        helpKeyItem("open", "↵", "Open the selected result", "enter return open run"),
        helpKeyItem("secondary", "⇧↵", "Secondary action, or the options of an action", "shift enter options argument"),
        helpKeyItem(
            "new-tab",
            `${modifierLabel}↵`,
            "Open in a new tab, keeping the palette open",
            "command control meta enter tab window",
        ),
        helpKeyItem("navigate", "↑↓", "Move through the results", "arrow up down navigate select"),
        helpKeyItem("category", "←→", "Move between categories, once the category row is selected", "arrow left right"),
        helpKeyItem("remove", "⌫", "Remove the active filter", "backspace delete scope action badge"),
        helpKeyItem("escape", "esc", "Clear the text, then the filter, then close", "escape back close clear"),
    ];
}

/**
 * One help row per action the user has: selecting it applies the `>` badge and
 * pre-fills the action's own title, so the row is the only one left to run.
 * Enter therefore means the same thing on every help row — it rewrites the
 * input, it never navigates.
 */
export function actionHelpItems(ctx: PaletteContext, handlers: PaletteHelpHandlers): PaletteItem[] {
    return (actionsProvider.emptyQueryItems?.(ctx) ?? []).map((action) => ({
        id: `help:action:${action.id}`,
        handler: () => {
            handlers.enterScope(ACTIONS_SCOPE);
            handlers.setText(action.title);
        },
        icon: action.icon,
        keywords: [action.keywords, action.subtitle].filter(Boolean).join(" "),
        shortcut: ACTIONS_SCOPE.key,
        // the action titles are rendered as they are everywhere else, so the
        // pre-filled query keeps matching the row it came from
        title: action.title,
    }));
}

/** The help panel: scopes, actions and key bindings, each ranked against the query */
export function helpSections(
    ctx: PaletteContext,
    query: string,
    modifierLabel: string,
    handlers: PaletteHelpHandlers,
): ResultSection[] {
    return [
        {
            id: "help:scopes",
            items: availableScopes(ctx).map((scope) => scopeHelpItem(scope, handlers.enterScope)),
            title: "Scopes",
        },
        { id: "help:actions", items: actionHelpItems(ctx, handlers), title: "Actions" },
        { id: "help:keys", items: helpKeyItems(modifierLabel), title: "Keys" },
    ].map((section) => ({ ...section, items: rankPaletteItems(section.items, query) }));
}
