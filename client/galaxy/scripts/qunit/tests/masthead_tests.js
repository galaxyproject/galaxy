/* global QUnit */
import $ from "jquery";
import testApp from "qunit/test-app";
import Masthead from "layout/masthead";
import { getAppRoot } from "onload";
import { getGalaxyInstance } from "app";

QUnit.module("Masthead test", {
    beforeEach: function() {
        testApp.create();
        this.masthead = new Masthead.View({
            brand: "brand",
            use_remote_user: "use_remote_user",
            remote_user_logout_href: "remote_user_logout_href",
            lims_doc_url: "lims_doc_url",
            biostar_url: "biostar_url",
            biostar_url_redirect: "biostar_url_redirect",
            support_url: "support_url",
            search_url: "search_url",
            mailing_lists: "mailing_lists",
            screencasts_url: "screencasts_url",
            wiki_url: "wiki_url",
            citation_url: "citation_url",
            terms_url: "terms_url",
            logo_url: "logo_url",
            logo_src: "../../../static/images/galaxyIcon_noText.png",
            is_admin_user: "is_admin_user",
            active_view: "analysis",
            ftp_upload_dir: "ftp_upload_dir",
            ftp_upload_site: "ftp_upload_site",
            datatypes_disable_auto: true,
            allow_user_creation: true,
            enable_cloud_launch: true,
            user_requests: true
        });
        this.container = this.masthead.render().$el;
        $("body").append(this.container);
    },
    afterEach: function() {
        testApp.destroy();
        this.container.remove();
    }
});

QUnit.test("tabs", function(assert) {
    var tab = this.masthead.collection.findWhere({ id: "analysis" });
    var $tab = $("#analysis");
    var $toggle = $tab.find(".nav-link");
    var $note = $tab.find(".nav-note");
    var $menu = $tab.find(".dropdown-menu");
    assert.ok(tab && $tab.length == 1, "Found analysis tab");
    tab.set("title", "Analyze");
    assert.ok($toggle.html() == "Analyze", "Correct title");
    assert.ok($toggle.css("visibility") == "visible", "Tab visible");
    tab.set("visible", false);
    assert.ok($toggle.css("visibility") == "hidden", "Tab hidden");
    tab.set("visible", true);
    assert.ok($toggle.css("visibility") == "visible", "Tab visible, again");
    assert.ok($toggle.attr("href") == getAppRoot(), "Correct initial url");
    tab.set("url", "_url");
    assert.ok($toggle.attr("href") == "/_url", "Correct test url");
    tab.set("url", "http://_url");
    assert.ok($toggle.attr("href") == "http://_url", "Correct http url");
    tab.set("tooltip", "_tooltip");
    $toggle.trigger("mouseover");
    assert.ok($(".tooltip-inner").html() == "_tooltip", "Correct tooltip");
    tab.set("tooltip", null);
    $toggle.trigger("mouseover");
    assert.ok($(".tooltip-inner").length === 0, "Tooltip removed");
    tab.set("tooltip", "_tooltip_new");
    $toggle.trigger("mouseover");
    assert.ok($(".tooltip-inner").html() == "_tooltip_new", "Correct new tooltip");
    tab.set("cls", "_cls");
    assert.ok($toggle.hasClass("_cls"), "Correct extra class");
    tab.set("cls", "_cls_new");
    assert.ok($toggle.hasClass("_cls_new") && !$toggle.hasClass("_cls"), "Correct new extra class");
    assert.ok($note.html() === "", "Correct empty note");
    tab.set({ note: "_note", show_note: true });
    assert.ok($note.html() == "_note", "Correct new note");
    tab.set("toggle", true);
    assert.ok($toggle.hasClass("toggle"), "Toggled");
    tab.set("toggle", false);
    assert.ok(!$tab.hasClass("toggle"), "Untoggled");
    tab.set("disabled", true);
    assert.ok($tab.hasClass("disabled"), "Correctly disabled");
    tab.set("disabled", false);
    assert.ok(!$tab.hasClass("disabled"), "Correctly enabled");
    assert.ok($tab.hasClass("active"), "Highlighted");
    tab.set("active", false);
    assert.ok(!$tab.hasClass("active"), "Not highlighted");
    tab.set("active", true);
    assert.ok($tab.hasClass("active"), "Highlighted, again");
    assert.ok($menu.length === 0, "Dropdown menu correctly empty");
    tab.set("menu", [{ title: "_menu_title", url: "_menu_url", target: "_menu_target" }]);
    $menu = $tab.find(".dropdown-menu");
    assert.ok($menu.hasClass("dropdown-menu"), "Menu has correct class");
    assert.ok($menu.css("display") == "none", "Menu hidden");
    $toggle.trigger("click");
    assert.ok($menu.css("display") == "block", "Menu shown");
    var $item = $menu.find("a");
    assert.ok($item.length == 1, "Added one menu item");
    assert.ok($item.html() == "_menu_title", "Menu item has correct title");
    assert.ok($item.attr("href") == "/_menu_url", "Menu item has correct url");
    assert.ok($item.attr("target") == "_menu_target", "Menu item has correct target");
    tab.set("menu", null);
    $item = $menu.find("a");
    assert.ok($item.length === 0, "All menu items removed");
    tab.set("menu", [
        { title: "_menu_title_0", url: "_menu_url_0", target: "_menu_target_0" },
        { title: "_menu_title_1", url: "_menu_url_1", target: "_menu_target_1" }
    ]);
    $item = $menu.find("a");
    assert.ok($item.length == 2, "Two menu items added");
    tab.set("show_menu", false);
    assert.ok($menu.css("display", "none"), "Menu manually hidden");
    tab.set("show_menu", true);
    assert.ok($menu.css("display", "block"), "Menu manually shown, again");
    tab = this.masthead.collection.findWhere({ id: "enable-scratchbook" });
    $tab = $("#enable-scratchbook");
    $toggle = $tab.find(".nav-link");
    assert.ok(tab && $toggle.length == 1, "Found tab to enable scratchbook");
    assert.ok(!$toggle.hasClass("toggle"), "Untoggled before click");
    $toggle.trigger("click");
    assert.ok($toggle.hasClass("toggle"), "Toggled after click");
    let galaxy = getGalaxyInstance();
    assert.ok(galaxy.frame.active, "Scratchbook is active");
});
