import galaxyOptions from "@tests/test-data/bootstrapped";
import { getGalaxyInstance, setGalaxyInstance } from "app";
import Backbone from "backbone";
import { suppressDebugConsole } from "tests/jest/helpers";

export function setupTestGalaxy(galaxyOptions_ = null) {
    galaxyOptions_ = galaxyOptions_ || galaxyOptions;
    setGalaxyInstance((GalaxyApp) => {
        const galaxy = new GalaxyApp(galaxyOptions_);
        galaxy.currHistoryPanel = {
            model: new Backbone.Model(),
        };
        return galaxy;
    });
}

// the app console debugs make sense but we just don't want to see them in test
// output.
suppressDebugConsole();

describe("App base construction/initializiation defaults", () => {
    beforeEach(() => {
        setupTestGalaxy(galaxyOptions);
    });

    test("App base construction/initializiation defaults", function () {
        const app = getGalaxyInstance();
        expect(app.options && typeof app.options === "object").toBeTruthy();
        expect(app.config && typeof app.config === "object").toBeTruthy();
        expect(app.user && typeof app.config === "object").toBeTruthy();
        expect(app.localize).toBe(window._l);
    });

    test("App base default options", function () {
        const app = getGalaxyInstance();
        expect(app.options !== undefined && typeof app.options === "object").toBeTruthy();
        expect(app.options.root).toBe("/");
        expect(app.options.patchExisting).toBe(true);
    });

    test("App base extends from Backbone.Events", function () {
        const app = getGalaxyInstance();
        ["on", "off", "trigger", "listenTo", "stopListening"].forEach(function (fn) {
            expect(Object.prototype.hasOwnProperty.call(app, fn) && typeof app[fn] === "function").toBeTruthy();
        });
    });

    // // We no longer want this behavior, but leaving the test to express that
    test("App base will patch in attributes from existing Galaxy objects", function () {
        const existingApp = getGalaxyInstance();
        existingApp.foo = 123;

        const newApp = setGalaxyInstance((GalaxyApp) => {
            return new GalaxyApp();
        });

        expect(newApp.foo === 123).toBeTruthy();
    });

    test("App base config", function () {
        const app = getGalaxyInstance();
        expect(app.config && typeof app.config === "object").toBeTruthy();
        expect(app.config.allow_user_deletion).toBe(false);
        expect(app.config.allow_user_creation).toBe(true);
        expect(app.config.wiki_url).toBe("https://galaxyproject.org/");
        expect(app.config.ftp_upload_site).toBe(null);
    });

    test("App base user", function () {
        const app = getGalaxyInstance();
        expect(app.user !== undefined && typeof app.user === "object").toBeTruthy();
        expect(app.user.isAdmin() === false).toBeTruthy();
    });
});
