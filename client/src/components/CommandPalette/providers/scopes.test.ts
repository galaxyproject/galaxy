import { describe, expect, it } from "vitest";

import type { PaletteContext } from "../types";
import { ACTIONS_SCOPE, availableScopes, findScope, isScopeAvailable, PALETTE_SCOPES } from "./scopes";

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

    it("requires a login for everything but tools and interactive tools", () => {
        const anonymous = PALETTE_SCOPES.filter((scope) => !scope.requiresLogin).map((scope) => scope.key);
        expect(anonymous).toEqual(["t", "it"]);
    });
});

describe("findScope", () => {
    it("matches keys exactly, ignoring case", () => {
        expect(findScope("w")?.label).toBe("My workflows");
        expect(findScope("W")?.label).toBe("My workflows");
        expect(findScope("hs")?.variant).toBe("shared");
        expect(findScope("IT")?.providerId).toBe("interactiveTools");
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

describe("isScopeAvailable", () => {
    it("hides login-only scopes from anonymous users", () => {
        const ctx = makeCtx({ isAnonymous: true });
        expect(isScopeAvailable(findScope("w")!, ctx)).toBe(false);
        expect(isScopeAvailable(findScope("t")!, ctx)).toBe(true);
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

    it("keeps the registry order while filtering", () => {
        expect(availableScopes(makeCtx({ isAnonymous: true })).map((scope) => scope.key)).toEqual(["t"]);
    });
});
