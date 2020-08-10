/* global QUnit */
import testApp from "../test-app";
import { getGalaxyInstance, setGalaxyInstance } from "app";

QUnit.module("Galaxy client app tests", {
    beforeEach: function () {
        testApp.create();
    },
    afterEach: function () {
        testApp.destroy();
    },
});

QUnit.test("App base construction/initializiation defaults", function (assert) {
    var app = getGalaxyInstance();
    assert.ok(app.hasOwnProperty("options") && typeof app.options === "object");
    assert.ok(app.hasOwnProperty("logger") && typeof app.logger === "object");
    assert.ok(app.hasOwnProperty("localize") && typeof app.localize === "function");
    assert.ok(app.hasOwnProperty("config") && typeof app.config === "object");
    assert.ok(app.hasOwnProperty("user") && typeof app.config === "object");
    assert.equal(app.localize, window._l);
});

QUnit.test("App base default options", function (assert) {
    var app = getGalaxyInstance();
    assert.ok(app.hasOwnProperty("options") && typeof app.options === "object");
    assert.equal(app.options.root, "/");
    assert.equal(app.options.patchExisting, true);
});

QUnit.test("App base extends from Backbone.Events", function (assert) {
    var app = getGalaxyInstance();
    ["on", "off", "trigger", "listenTo", "stopListening"].forEach(function (fn) {
        assert.ok(app.hasOwnProperty(fn) && typeof app[fn] === "function");
    });
});

QUnit.test("App base has logging methods from utils/add-logging.js", function (assert) {
    var app = getGalaxyInstance();
    ["debug", "info", "warn", "error", "metric"].forEach(function (fn) {
        assert.ok(typeof app[fn] === "function");
    });
    assert.ok(app._logNamespace === "GalaxyApp");
});

// We no longer want this behavior
QUnit.test("App base will patch in attributes from existing Galaxy objects", function (assert) {
    var existingApp = getGalaxyInstance();
    existingApp.foo = 123;

    var newApp = setGalaxyInstance((GalaxyApp) => {
        return new GalaxyApp();
    });

    assert.ok(newApp.foo === 123);
});

QUnit.test("App base logger", function (assert) {
    var app = getGalaxyInstance();
    assert.ok(app.hasOwnProperty("logger") && typeof app.config === "object");
});

QUnit.test("App base config", function (assert) {
    var app = getGalaxyInstance();
    assert.ok(app.hasOwnProperty("config") && typeof app.config === "object");
    assert.equal(app.config.allow_user_deletion, false);
    assert.equal(app.config.allow_user_creation, true);
    assert.equal(app.config.wiki_url, "https://galaxyproject.org/");
    assert.equal(app.config.ftp_upload_site, null);
});

QUnit.test("App base user", function (assert) {
    var app = getGalaxyInstance();
    assert.ok(app.hasOwnProperty("user") && typeof app.user === "object");
    assert.ok(app.user.isAdmin() === false);
});
