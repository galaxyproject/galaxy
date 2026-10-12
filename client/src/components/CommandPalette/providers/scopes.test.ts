import { describe, expect, it } from "vitest";

import { ensureDefined } from "@/utils/assertions";

import { makeCtx } from "../test-utils";
import { parsePaletteQuery } from "../utilities";
import {
    ACTIONS_SCOPE,
    availableScopes,
    findScope,
    isProviderEnabled,
    isScopeAvailable,
    isScopeLoginGated,
    loginGatedScopes,
    PALETTE_SCOPES,
    type ScopeDefinition,
} from "./scopes";

describe("PALETTE_SCOPES", () => {
    it("has unique lowercase keys of at most two letters", () => {
        const keys = PALETTE_SCOPES.map((scope) => scope.key);
        expect(new Set(keys).size).toBe(keys.length);
        keys.forEach((key) => expect(key).toMatch(/^[a-z]{1,2}$/));
    });

    it("keeps every key typeable as a scope token", () => {
        // a key the token pattern does not accept (e.g. three letters) could never be entered
        PALETTE_SCOPES.forEach((scope) => {
            expect(parsePaletteQuery(`${scope.key}:fastqc`)).toEqual({ type: "scope", scope, query: "fastqc" });
        });
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
        expect(anonymous).toEqual(["wp", "t", "hp", "rp", "it", "n"]);
    });

    it("keeps the own and shared-with-me scopes behind a login", () => {
        const gated = PALETTE_SCOPES.filter((scope) => scope.requiresLogin).map((scope) => scope.key);
        expect(gated).toEqual(["w", "ws", "h", "hs", "ha", "d", "v", "i", "r"]);
    });
});

describe("findScope", () => {
    it.each([
        { key: "w", field: "label", expected: "My workflows" },
        { key: "W", field: "label", expected: "My workflows" },
        { key: "hs", field: "variant", expected: "shared" },
        { key: "IT", field: "providerId", expected: "interactiveTools" },
        { key: "n", field: "providerId", expected: "navigation" },
    ] as const)("resolves exact key '$key' to $field '$expected', ignoring case", ({ key, field, expected }) => {
        expect(ensureDefined(findScope(key))[field]).toBe(expected);
    });

    it.each(["wz", "x", "wps", ""])("does not fall back to a shorter or longer key for '%s'", (key) => {
        expect(findScope(key)).toBeUndefined();
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
        expect(isScopeAvailable(ensureDefined(findScope("w")), ctx)).toBe(false);
        expect(isScopeAvailable(ensureDefined(findScope("ws")), ctx)).toBe(false);
        expect(isScopeAvailable(ensureDefined(findScope("t")), ctx)).toBe(true);
        expect(isScopeAvailable(ensureDefined(findScope("n")), ctx)).toBe(true);
    });

    it("offers the public scopes to anonymous users", () => {
        const ctx = makeCtx({ isAnonymous: true });
        expect(isScopeAvailable(ensureDefined(findScope("wp")), ctx)).toBe(true);
        expect(isScopeAvailable(ensureDefined(findScope("hp")), ctx)).toBe(true);
        expect(isScopeAvailable(ensureDefined(findScope("rp")), ctx)).toBe(true);
    });

    it("hides interactive tools unless they are enabled", () => {
        const scope = ensureDefined(findScope("it"));
        expect(isScopeAvailable(scope, makeCtx())).toBe(false);
        expect(isScopeAvailable(scope, makeCtx({ config: { interactivetools_enable: true } }))).toBe(true);
    });

    it("lists every scope for a logged-in user on a fully featured instance", () => {
        const ctx = makeCtx({ config: { interactivetools_enable: true } });
        expect(availableScopes(ctx)).toEqual(PALETTE_SCOPES);
    });

    it("hides every scope of a disabled provider, variants included", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["workflows"] } });
        expect(isScopeAvailable(ensureDefined(findScope("w")), ctx)).toBe(false);
        expect(isScopeAvailable(ensureDefined(findScope("ws")), ctx)).toBe(false);
        expect(isScopeAvailable(ensureDefined(findScope("wp")), ctx)).toBe(false);
        expect(isScopeAvailable(ensureDefined(findScope("h")), ctx)).toBe(true);
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
            "rp",
            "n",
        ]);
    });
});

describe("isScopeLoginGated", () => {
    it("names the scopes an account alone stands between", () => {
        const ctx = makeCtx({ isAnonymous: true });
        expect(isScopeLoginGated(ensureDefined(findScope("w")), ctx)).toBe(true);
        expect(isScopeLoginGated(ensureDefined(findScope("d")), ctx)).toBe(true);
        // public, so nothing is being kept from anyone
        expect(isScopeLoginGated(ensureDefined(findScope("wp")), ctx)).toBe(false);
    });

    it("gates nothing for a user who is logged in", () => {
        expect(isScopeLoginGated(ensureDefined(findScope("w")), makeCtx())).toBe(false);
    });

    it("stays silent about a scope of a provider the instance disabled", () => {
        const ctx = makeCtx({ isAnonymous: true, config: { command_palette_disabled_providers: ["workflows"] } });
        expect(isScopeLoginGated(ensureDefined(findScope("w")), ctx)).toBe(false);
        expect(isScopeLoginGated(ensureDefined(findScope("h")), ctx)).toBe(true);
    });

    it("stays silent while a config gate of the scope's own is unmet", () => {
        const scope: ScopeDefinition = {
            key: "x",
            label: "Gated",
            providerId: "workflows",
            requiresLogin: true,
            configGate: (ctx) => Boolean(ctx.config.interactivetools_enable),
        };
        expect(isScopeLoginGated(scope, makeCtx({ isAnonymous: true }))).toBe(false);
        expect(
            isScopeLoginGated(scope, makeCtx({ isAnonymous: true, config: { interactivetools_enable: true } })),
        ).toBe(true);
    });

    it("lists the gated scopes in registry order", () => {
        expect(loginGatedScopes(makeCtx({ isAnonymous: true })).map((scope) => scope.key)).toEqual([
            "w",
            "ws",
            "h",
            "hs",
            "ha",
            "d",
            "v",
            "i",
            "r",
        ]);
        expect(loginGatedScopes(makeCtx())).toEqual([]);
    });
});
