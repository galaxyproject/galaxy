import { computed, shallowRef } from "vue";

import type { ScopeDefinition } from "./providers/scopes";
import type { PaletteItem } from "./types";
import { parsePaletteQuery } from "./utilities";

/**
 * What the palette is currently searching. Everything but `root` is rendered
 * as a removable badge chip in front of the input.
 */
export type PaletteMode =
    | { type: "root" }
    | { type: "scoped"; scope: ScopeDefinition }
    | { type: "action"; action: PaletteItem }
    | { type: "help" };

/** What the caller has to do after {@link usePaletteMachine} handled escape */
export type EscapeResult = "cleared-text" | "popped-mode" | "close";

/**
 * Input state machine of the command palette: the current mode plus the text
 * left in the input after any recognized token was converted into a badge.
 *
 * Palette-local by design — one instance per palette component, so it stays a
 * plain composable instead of a store, and every transition is a pure function
 * of the current state.
 */
export function usePaletteMachine() {
    const mode = shallowRef<PaletteMode>({ type: "root" });
    const text = shallowRef("");

    /** Search text without the badge token, trimmed for providers */
    const query = computed(() => text.value.trim());

    const scope = computed(() => (mode.value.type === "scoped" ? mode.value.scope : undefined));

    /** Label of the badge chip, unset while in root or help mode */
    const badgeLabel = computed(() => {
        switch (mode.value.type) {
            case "scoped":
                return mode.value.scope.label;
            case "action":
                return mode.value.action.title;
            default:
                return undefined;
        }
    });

    /** Converts a scope into a badge and clears the input */
    function enterScope(next: ScopeDefinition) {
        mode.value = { type: "scoped", scope: next };
        text.value = "";
    }

    /** Converts an action into a badge collecting its argument */
    function enterAction(action: PaletteItem) {
        mode.value = { type: "action", action };
        text.value = "";
    }

    function enterHelp() {
        mode.value = { type: "help" };
        text.value = "";
    }

    /** Drops the badge, keeping whatever was typed after it */
    function popMode() {
        if (mode.value.type !== "root") {
            mode.value = { type: "root" };
        }
    }

    /**
     * Applies raw input. A recognized token (`>` or `x:`) becomes a badge and
     * is stripped, a lone `?` in root opens help, anything else is kept as
     * typed — trailing spaces included, so words can be typed normally.
     */
    function setText(next: string) {
        const parsed = parsePaletteQuery(next);
        if (parsed.type === "scope") {
            enterScope(parsed.scope);
            text.value = parsed.query;
            return;
        }
        if (parsed.type === "help" && (mode.value.type === "root" || mode.value.type === "help")) {
            enterHelp();
            return;
        }
        text.value = next;
    }

    /** Stepwise escape: clear the text, then the badge, then close */
    function handleEscape(): EscapeResult {
        if (text.value !== "") {
            text.value = "";
            return "cleared-text";
        }
        if (mode.value.type !== "root") {
            popMode();
            return "popped-mode";
        }
        return "close";
    }

    function reset() {
        mode.value = { type: "root" };
        text.value = "";
    }

    return {
        badgeLabel,
        enterAction,
        enterHelp,
        enterScope,
        handleEscape,
        mode,
        popMode,
        query,
        reset,
        scope,
        setText,
        text,
    };
}
