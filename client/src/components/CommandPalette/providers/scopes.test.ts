import { describe, expect, it } from "vitest";

import type { PaletteContext } from "../types";
import {
    ACTIONS_SCOPE,
    availableScopes,
    findScope,
    isProviderEnabled,
    isScopeAvailable,
    PALETTE_SCOPES,
} from "./scopes";

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous: false, ...overrides };
}

describe("PALETTE_SCOPES", () => {
    it("has unique lowercase keys of at most two letters", () => {
        const keys = PALETTE_SCOPES.map((scope) => scope.key);
        expect(new Set(keys).size).toBe(keys.length);
        keys.forEach((key) => expect(key).toMatch(/^[a-z]{1,2}$/));
    });

    it("groups variants of one entity under a single provider", () => {
        const workflows = PALETTE_SCOPES.filter((scope) => scope.providerId === "workflows");
        expect(workflows.map((scope) => [scope.key, scope.variant])).toEqual([
            ["w", undefined],
            ["ws", "shared"],
            ["wp", "published"],
        ]);
        const histories = PALETTE_SCOPES.filter((scope) => scope.providerId === "histories");
        expect(histories.map((scope) => scope.key)).toEqual(["h", "hs", "hp", "ha"]);
    });

    it("leaves the public scopes, tools and navigation open to anonymous users", () => {
        const anonymous = PALETTE_SCOPES.filter((scope) => !scope.requiresLogin).map((scope) => scope.key);
        expect(anonymous).toEqual(["wp", "t", "hp", "pp", "it", "n"]);
    });

    it("keeps the own and shared-with-me scopes behind a login", () => {
        const gated = PALETTE_SCOPES.filter((scope) => scope.requiresLogin).map((scope) => scope.key);
        expect(gated).toEqual(["w", "ws", "h", "hs", "ha", "d", "v", "i", "p"]);
    });
});

describe("findScope", () => {
    it("matches keys exactly, ignoring case", () => {
        expect(findScope("w")?.label).toBe("My workflows");
        expect(findScope("W")?.label).toBe("My workflows");
        expect(findScope("hs")?.variant).toBe("shared");
        expect(findScope("IT")?.providerId).toBe("interactiveTools");
        expect(findScope("n")?.providerId).toBe("navigation");
    });

    it("never falls back to a shorter or longer key", () => {
        expect(findScope("wz")).toBeUndefined();
        expect(findScope("x")).toBeUndefined();
        expect(findScope("wps")).toBeUndefined();
        expect(findScope("")).toBeUndefined();
    });

    it("does not resolve the actions sigil", () => {
        expect(findScope(">")).toBeUndefined();
        expect(ACTIONS_SCOPE.providerId).toBe("actions");
    });
});

describe("isProviderEnabled", () => {
    it("enables every provider while the instance disables none", () => {
        expect(isProviderEnabled("workflows", makeCtx())).toBe(true);
        expect(isProviderEnabled("workflows", makeCtx({ config: { command_palette_disabled_providers: [] } }))).toBe(
            true,
        );
    });

    it("disables exactly the providers the instance names", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["workflows", "actions"] } });
        expect(isProviderEnabled("workflows", ctx)).toBe(false);
        expect(isProviderEnabled("actions", ctx)).toBe(false);
        expect(isProviderEnabled("histories", ctx)).toBe(true);
    });
});

describe("isScopeAvailable", () => {
    it("hides login-only scopes from anonymous users", () => {
        const ctx = makeCtx({ isAnonymous: true });
        expect(isScopeAvailable(findScope("w")!, ctx)).toBe(false);
        expect(isScopeAvailable(findScope("ws")!, ctx)).toBe(false);
        expect(isScopeAvailable(findScope("t")!, ctx)).toBe(true);
        expect(isScopeAvailable(findScope("n")!, ctx)).toBe(true);
    });

    it("offers the public scopes to anonymous users", () => {
        const ctx = makeCtx({ isAnonymous: true });
        expect(isScopeAvailable(findScope("wp")!, ctx)).toBe(true);
        expect(isScopeAvailable(findScope("hp")!, ctx)).toBe(true);
        expect(isScopeAvailable(findScope("pp")!, ctx)).toBe(true);
    });

    it("hides interactive tools unless they are enabled", () => {
        const scope = findScope("it")!;
        expect(isScopeAvailable(scope, makeCtx())).toBe(false);
        expect(isScopeAvailable(scope, makeCtx({ config: { interactivetools_enable: true } }))).toBe(true);
    });

    it("lists every scope for a logged-in user on a fully featured instance", () => {
        const ctx = makeCtx({ config: { interactivetools_enable: true } });
        expect(availableScopes(ctx)).toEqual(PALETTE_SCOPES);
    });

    it("hides every scope of a disabled provider, variants included", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["workflows"] } });
        expect(isScopeAvailable(findScope("w")!, ctx)).toBe(false);
        expect(isScopeAvailable(findScope("ws")!, ctx)).toBe(false);
        expect(isScopeAvailable(findScope("wp")!, ctx)).toBe(false);
        expect(isScopeAvailable(findScope("h")!, ctx)).toBe(true);
        expect(availableScopes(ctx).map((scope) => scope.providerId)).not.toContain("workflows");
    });

    it("gates the actions sigil on its own provider", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["actions"] } });
        expect(isScopeAvailable(ACTIONS_SCOPE, makeCtx())).toBe(true);
        expect(isScopeAvailable(ACTIONS_SCOPE, ctx)).toBe(false);
    });

    it("keeps the registry order while filtering", () => {
        expect(availableScopes(makeCtx({ isAnonymous: true })).map((scope) => scope.key)).toEqual([
            "wp",
            "t",
            "hp",
            "pp",
            "n",
        ]);
    });
});
