import { computed, shallowRef } from "vue";

import { isScopeAvailable, type ScopeDefinition } from "./providers/scopes";
import type { PaletteContext, PaletteItem } from "./types";
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
 *
 * @param getContext Resolves the current palette context, used to reject scope
 * tokens the user may not use at all — `hs:` while anonymous, `it:` on an
 * instance without interactive tools. Omitting it treats every scope as
 * available, which keeps the parsing tests context free.
 */
export function usePaletteMachine(getContext?: () => PaletteContext) {
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

    /**
     * Whether a token typed into the input may turn into a badge. A scope the
     * help panel never offers must not be reachable by typing it either, so a
     * gated token stays plain search text.
     */
    function scopeAllowed(next: ScopeDefinition) {
        const ctx = getContext?.();
        return ctx ? isScopeAvailable(next, ctx) : true;
    }

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

    /**
     * Leaves an action's argument mode, dropping the argument with it. Every
     * other mode is left alone: only an action stops `setText` from parsing, so
     * only an action may not outlive the palette it was entered in.
     */
    function exitAction() {
        if (mode.value.type === "action") {
            mode.value = { type: "root" };
            text.value = "";
        }
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
     * typed — trailing spaces included, so words can be typed normally. While
     * an action collects its argument nothing is parsed at all. A token naming
     * a scope the current user may not use stays plain text as well.
     */
    function setText(next: string) {
        if (mode.value.type === "action") {
            // an argument is free text — neither a scope token nor `?` may steal it
            text.value = next;
            return;
        }
        const parsed = parsePaletteQuery(next);
        if (parsed.type === "scope" && scopeAllowed(parsed.scope)) {
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

    return {
        badgeLabel,
        enterAction,
        enterHelp,
        enterScope,
        exitAction,
        handleEscape,
        mode,
        popMode,
        query,
        scope,
        setText,
        text,
    };
}
