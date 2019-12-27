/* global QUnit */
import $ from "jquery";
import testApp from "qunit/test-app";
import DefaultView from "mvc/upload/default/default-view";
import Backbone from "backbone";

QUnit.module("Upload dialog test", {
    beforeEach: function() {
        testApp.create();
        const uploadApp = {
            currentFtp: () => {
                return "ftp://localhost/";
            },
            currentHistory: () => {
                return "1245";
            },
            show: () => {
                return;
            },
            model: new Backbone.Model(),
            toData: () => {
                return {};
            }
        };
        this.view = new DefaultView({ app: uploadApp });
        $("body").append(this.view.el);
    },
    afterEach: function() {
        testApp.destroy();
    }
});

QUnit.test("test initial dialog state", function(assert) {
    this.view.render();
    assert.ok(this.view.collection.length == 0, "Invalid initial upload item collection.");
    assert.ok($("#btn-start").hasClass("disabled"), "Start button should be disabled.");
    assert.ok($("#btn-stop").hasClass("disabled"), "Stop button should be disabled.");
    assert.ok($("#btn-reset").hasClass("disabled"), "Reset button should be disabled.");
});

QUnit.test("test adding/removing paste/fetch upload item", function(assert) {
    this.view.render();
    $("#btn-new").trigger("click");
    assert.ok(!$("#btn-start").hasClass("disabled"), "Start button should be enabled.");
    assert.ok($("#btn-stop").hasClass("disabled"), "Stop button should (still) be disabled.");
    assert.ok(!$("#btn-reset").hasClass("disabled"), "Reset button should be enabled.");
    assert.ok(this.view.collection.length == 1, "Invalid upload item collection length after adding item.");
    assert.ok(
        $("#btn-new")
            .find("i")
            .hasClass("fa-edit"),
        "Paste/fetch icon changed"
    );
    assert.ok($("#btn-start").hasClass("btn-primary"), "Start button should be enabled/highlighted.");
    assert.ok(
        $("#upload-row-0")
            .find(".upload-symbol")
            .hasClass("fa-trash-o"),
        "Should show regular trash icon."
    );
    $("#upload-row-0")
        .find(".popover-close")
        .trigger("click");
    $("#btn-start").trigger("click");
    /*
    assert.ok(
        $("#upload-row-0")
            .find(".upload-symbol")
            .hasClass("fa-exclamation-triangle"),
        "Upload attempt should have failed."
    );
    $("#upload-row-0")
        .find(".upload-symbol")
        .trigger("click");
    assert.ok(this.view.collection.length == 0, "Removing item from collection failed.");
    */
});

QUnit.test("test ftp popup", function(assert) {
    this.view.render();
    $("#btn-ftp").trigger("click");
    assert.ok($(".upload-ftp").length == 1, "Should show ftp popover.");
});
