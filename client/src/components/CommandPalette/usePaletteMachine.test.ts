import { describe, expect, it } from "vitest";

import { ACTIONS_SCOPE, findScope } from "./providers/scopes";
import type { PaletteContext, PaletteItem } from "./types";
import { usePaletteMachine } from "./usePaletteMachine";

const WORKFLOWS = findScope("w")!;

const NEW_HISTORY: PaletteItem = { id: "actions:new-history", title: "Create new history" };

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return {
        canUseUnprivilegedTools: false,
        config: { interactivetools_enable: false, llm_api_configured: false },
        isAdmin: false,
        isAnonymous: false,
        ...overrides,
    };
}

describe("usePaletteMachine", () => {
    it("starts in root mode with an empty input", () => {
        const machine = usePaletteMachine();
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.text.value).toBe("");
        expect(machine.badgeLabel.value).toBeUndefined();
    });

    it("keeps plain text exactly as typed", () => {
        const machine = usePaletteMachine();
        machine.setText("rna ");
        expect(machine.mode.value).toEqual({ type: "root" });
        // trailing spaces survive so multi-word queries can be typed
        expect(machine.text.value).toBe("rna ");
        expect(machine.query.value).toBe("rna");
    });

    it("converts a scope token into a badge and strips it", () => {
        const machine = usePaletteMachine();
        machine.setText("w:");
        expect(machine.mode.value).toEqual({ type: "scoped", scope: WORKFLOWS });
        expect(machine.scope.value).toBe(WORKFLOWS);
        expect(machine.text.value).toBe("");
        expect(machine.badgeLabel.value).toBe("My workflows");
    });

    it("keeps the text typed after a two-letter token", () => {
        const machine = usePaletteMachine();
        machine.setText("hs: shared");
        expect(machine.scope.value?.key).toBe("hs");
        expect(machine.text.value).toBe("shared");
    });

    it("converts '>' into the actions badge", () => {
        const machine = usePaletteMachine();
        machine.setText("> up");
        expect(machine.mode.value).toEqual({ type: "scoped", scope: ACTIONS_SCOPE });
        expect(machine.badgeLabel.value).toBe("Actions");
        expect(machine.text.value).toBe("up");
    });

    it("leaves unknown tokens as search text", () => {
        const machine = usePaletteMachine();
        machine.setText("name:fastqc");
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.text.value).toBe("name:fastqc");
    });

    it("keeps a login-only token as plain text for anonymous users", () => {
        const machine = usePaletteMachine(() => makeCtx({ isAnonymous: true }));
        machine.setText("hs: shared");
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.text.value).toBe("hs: shared");
        // an ungated scope still works while anonymous
        machine.setText("t: align");
        expect(machine.scope.value?.key).toBe("t");
    });

    it("keeps a config-gated token as plain text until the config allows it", () => {
        const gated = usePaletteMachine(() => makeCtx());
        gated.setText("it: jupyter");
        expect(gated.mode.value).toEqual({ type: "root" });
        expect(gated.text.value).toBe("it: jupyter");

        const enabled = usePaletteMachine(() => makeCtx({ config: { interactivetools_enable: true } }));
        enabled.setText("it: jupyter");
        expect(enabled.scope.value?.key).toBe("it");
        expect(enabled.text.value).toBe("jupyter");
    });

    it("never gates the actions sigil", () => {
        const machine = usePaletteMachine(() => makeCtx({ isAnonymous: true }));
        machine.setText("> up");
        expect(machine.mode.value).toEqual({ type: "scoped", scope: ACTIONS_SCOPE });
    });

    it("switches directly from one scope to another", () => {
        const machine = usePaletteMachine();
        machine.setText("w:");
        machine.setText("t: align");
        expect(machine.scope.value?.key).toBe("t");
        expect(machine.text.value).toBe("align");
    });

    it("opens help for a lone '?' in root mode", () => {
        const machine = usePaletteMachine();
        machine.setText("?");
        expect(machine.mode.value).toEqual({ type: "help" });
        expect(machine.text.value).toBe("");
        expect(machine.badgeLabel.value).toBeUndefined();
    });

    it("treats '?' inside a scope as search text", () => {
        const machine = usePaletteMachine();
        machine.setText("t:");
        machine.setText("?");
        expect(machine.scope.value?.key).toBe("t");
        expect(machine.text.value).toBe("?");
    });

    it("enters scopes and actions programmatically", () => {
        const machine = usePaletteMachine();
        machine.setText("rna");
        machine.enterScope(WORKFLOWS);
        expect(machine.text.value).toBe("");
        machine.enterAction(NEW_HISTORY);
        expect(machine.mode.value).toEqual({ type: "action", action: NEW_HISTORY });
        expect(machine.badgeLabel.value).toBe("Create new history");
    });

    it("collects the argument of an action and steps back out of it", () => {
        const machine = usePaletteMachine();
        machine.enterAction(NEW_HISTORY);
        machine.setText("rna analysis");
        expect(machine.mode.value).toEqual({ type: "action", action: NEW_HISTORY });
        expect(machine.query.value).toBe("rna analysis");

        expect(machine.handleEscape()).toBe("cleared-text");
        expect(machine.mode.value).toEqual({ type: "action", action: NEW_HISTORY });

        expect(machine.handleEscape()).toBe("popped-mode");
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.badgeLabel.value).toBeUndefined();
    });

    it("keeps a scope token typed as an argument as plain text", () => {
        const machine = usePaletteMachine();
        machine.enterAction(NEW_HISTORY);
        machine.setText("w: my run");
        // an argument is free text, the scope parser must not steal it
        expect(machine.mode.value).toEqual({ type: "action", action: NEW_HISTORY });
        expect(machine.text.value).toBe("w: my run");
    });

    it("pops the badge but keeps the typed text", () => {
        const machine = usePaletteMachine();
        machine.setText("w: rna");
        machine.popMode();
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.text.value).toBe("rna");
        expect(machine.badgeLabel.value).toBeUndefined();
    });

    it("ignores popMode in root mode", () => {
        const machine = usePaletteMachine();
        machine.setText("rna");
        machine.popMode();
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.text.value).toBe("rna");
    });

    it("escapes stepwise: text, then badge, then close", () => {
        const machine = usePaletteMachine();
        machine.setText("w: rna");

        expect(machine.handleEscape()).toBe("cleared-text");
        expect(machine.text.value).toBe("");
        expect(machine.scope.value).toBe(WORKFLOWS);

        expect(machine.handleEscape()).toBe("popped-mode");
        expect(machine.mode.value).toEqual({ type: "root" });

        expect(machine.handleEscape()).toBe("close");
    });

    it("escapes out of help mode before closing", () => {
        const machine = usePaletteMachine();
        machine.setText("?");
        expect(machine.handleEscape()).toBe("popped-mode");
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.handleEscape()).toBe("close");
    });

    it("resets mode and text", () => {
        const machine = usePaletteMachine();
        machine.setText("w: rna");
        machine.reset();
        expect(machine.mode.value).toEqual({ type: "root" });
        expect(machine.text.value).toBe("");
    });
});
