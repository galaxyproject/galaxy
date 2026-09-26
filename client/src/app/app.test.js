import galaxyOptions from "@tests/test-data/bootstrapped";
import { suppressDebugConsole } from "@tests/vitest/helpers";
import { beforeEach, describe, expect, test } from "vitest";

import { getGalaxyInstance, setGalaxyInstance } from "@/app";
import { GalaxyApp } from "@/app/galaxy";

export function setupTestGalaxy(galaxyOptions_ = null) {
    galaxyOptions_ = galaxyOptions_ || galaxyOptions;
    const app = new GalaxyApp(galaxyOptions_);
    setGalaxyInstance(app);
}

// suppress console noise
suppressDebugConsole();

describe("App base construction/initialization defaults", () => {
    beforeEach(() => {
        setupTestGalaxy(galaxyOptions);
    });

    test("App base construction/initialization defaults", () => {
        const app = getGalaxyInstance();
        expect(app.options && typeof app.options === "object").toBeTruthy();
        expect(app.config && typeof app.config === "object").toBeTruthy();
        expect(app.user && typeof app.config === "object").toBeTruthy();
        expect(app.localize).toBe(window._l);
    });

    test("App base default options", () => {
        const app = getGalaxyInstance();
        expect(app.options !== undefined && typeof app.options === "object").toBeTruthy();
        expect(app.options.root).toBe("/");
        expect(app.options.patchExisting).toBe(true);
    });

    // we no longer patch attributes from existing Galaxy objects, test expresses that
    test("App base will patch in attributes from existing Galaxy objects", () => {
        const existingApp = getGalaxyInstance();
        existingApp.foo = 123;

        const newApp = new GalaxyApp();
        setGalaxyInstance(newApp);

        expect(newApp.foo).toBeUndefined();
    });

    test("App base config", () => {
        const app = getGalaxyInstance();
        expect(app.config && typeof app.config === "object").toBeTruthy();
        expect(app.config.allow_user_deletion).toBe(false);
        expect(app.config.allow_local_account_creation).toBe(true);
        expect(app.config.wiki_url).toBe("https://galaxyproject.org/");
        expect(app.config.ftp_upload_site).toBe(null);
    });

    test("App base user", () => {
        const app = getGalaxyInstance();
        expect(app.user !== undefined && typeof app.user === "object").toBeTruthy();
        expect(app.user.isAdmin()).toBe(false);
    });
});
