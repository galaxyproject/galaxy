/* global define */
import testApp from "qunit/test-app";
import { GalaxyApp } from "galaxy";
import $ from "jquery";

QUnit.module("Galaxy client app tests");

var options = {
    config: {
        allow_user_deletion: false,
        allow_user_creation: true,
        wiki_url: "https://galaxyproject.org/",
        ftp_upload_site: null,
        support_url: "https://galaxyproject.org/support/",
        allow_user_dataset_purge: false,
        allow_library_path_paste: false,
        user_library_import_dir: null,
        terms_url: null,
        ftp_upload_dir: null,
        library_import_dir: null,
        logo_url: null,
        enable_unique_workflow_defaults: false
    },
    user: {
        username: "test",
        quota_percent: null,
        total_disk_usage: 61815527,
        nice_total_disk_usage: "59.0 MB",
        email: "test@test.test",
        tags_used: ["test"],
        model_class: "User",
        id: "f2db41e1fa331b3e"
    }
};

QUnit.test("App base construction/initializiation defaults", function(assert) {
    var app = new GalaxyApp({});
    assert.ok(app.hasOwnProperty("options") && typeof app.options === "object");
    assert.ok(app.hasOwnProperty("logger") && typeof app.logger === "object");
    assert.ok(app.hasOwnProperty("localize") && typeof app.localize === "function");
    assert.ok(app.hasOwnProperty("config") && typeof app.config === "object");
    assert.ok(app.hasOwnProperty("user") && typeof app.config === "object");
    assert.equal(app.localize, window._l);
});

QUnit.test("App base default options", function(assert) {
    var app = new GalaxyApp({});
    assert.ok(app.hasOwnProperty("options") && typeof app.options === "object");
    assert.equal(app.options.root, "/");
    assert.equal(app.options.patchExisting, true);
});

QUnit.test("App base extends from Backbone.Events", function(assert) {
    var app = new GalaxyApp({});
    ["on", "off", "trigger", "listenTo", "stopListening"].forEach(function(fn) {
        assert.ok(app.hasOwnProperty(fn) && typeof app[fn] === "function");
    });
});

QUnit.test("App base has logging methods from utils/add-logging.js", function(assert) {
    var app = new GalaxyApp({});
    ["debug", "info", "warn", "error", "metric"].forEach(function(fn) {
        assert.ok(typeof app[fn] === "function");
    });
    assert.ok(app._logNamespace === "GalaxyApp");
});

QUnit.test("App base will patch in attributes from existing Galaxy objects", function(assert) {
    window.Galaxy = {
        attribute: {
            subattr: 1
        }
    };
    var app = new GalaxyApp({});
    assert.ok(typeof app.attribute === "object" && app.attribute.subattr === 1);
});

QUnit.test("App base logger", function(assert) {
    var app = new GalaxyApp({});
    assert.ok(app.hasOwnProperty("logger") && typeof app.config === "object");
});

QUnit.test("App base config", function(assert) {
    var app = new GalaxyApp(options);
    assert.ok(app.hasOwnProperty("config") && typeof app.config === "object");
    assert.equal(app.config.allow_user_deletion, false);
    assert.equal(app.config.allow_user_creation, true);
    assert.equal(app.config.wiki_url, "https://galaxyproject.org/");
    assert.equal(app.config.ftp_upload_site, null);
});

QUnit.test("App base user", function(assert) {
    var app = new GalaxyApp({});
    assert.ok(app.hasOwnProperty("user") && typeof app.user === "object");
    assert.ok(app.user.isAdmin() === false);
});
