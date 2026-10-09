import galaxyOptions from "@tests/test-data/bootstrapped";
import { suppressDebugConsole } from "@tests/vitest/helpers";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getGalaxyInstance, setGalaxyInstance } from "@/app";
import { GalaxyApp } from "@/app/galaxy";

describe("GalaxyApp", () => {
    let app;
    let previousLocale;

    beforeEach(() => {
        suppressDebugConsole();
        vi.stubGlobal("_galaxyInstance", undefined);
        vi.stubGlobal("_l", window._l);
        previousLocale = sessionStorage.getItem("currentLocale");
        app = new GalaxyApp(galaxyOptions);
        setGalaxyInstance(app);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        if (previousLocale === null) {
            sessionStorage.removeItem("currentLocale");
        } else {
            sessionStorage.setItem("currentLocale", previousLocale);
        }
    });

    it("initializes the registered instance with options, config, user and localization", () => {
        expect(getGalaxyInstance()).toBe(app);
        expect(app.options).toBeTypeOf("object");
        expect(app.options).toBeTruthy();
        expect(app.config).toBeTypeOf("object");
        expect(app.config).toBeTruthy();
        expect(app.user).toBeTypeOf("object");
        expect(app.user).toBeTruthy();
        expect(app.localize).toBe(window._l);
    });

    it("uses default root and patchExisting options when omitted", () => {
        expect(app.options).toBeTypeOf("object");
        expect(app.options).toBeTruthy();
        expect(app.options.root).toBe("/");
        expect(app.options.patchExisting).toBe(true);
    });

    it("does not copy attributes from the previously registered instance", () => {
        app.foo = 123;

        const replacement = new GalaxyApp();
        setGalaxyInstance(replacement);

        expect(replacement.foo).toBeUndefined();
    });

    it("uses the bootstrapped configuration", () => {
        expect(app.config).toBeTypeOf("object");
        expect(app.config).toBeTruthy();
        expect(app.config.allow_user_deletion).toBe(false);
        expect(app.config.allow_local_account_creation).toBe(true);
        expect(app.config.wiki_url).toBe("https://galaxyproject.org/");
        expect(app.config.ftp_upload_site).toBe(null);
    });

    it("initializes a non-admin user from bootstrapped data", () => {
        expect(app.user).toBeTypeOf("object");
        expect(app.user.isAdmin()).toBe(false);
    });
});
