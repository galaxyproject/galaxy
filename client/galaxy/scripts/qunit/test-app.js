/** Creates a generic/global Galaxy environment, loads shared libraries and a fake server */
/* global define */

define([
    "jquery",
    "sinon",
    "bootstrap",
    "backbone",
    "qunit/test-data/bootstrapped",
    "qunit/test-data/fakeserver",
    "galaxy",
    "libs/jquery/select2",
    "libs/jquery/jquery-ui"
], function($, sinon, bootstrap, Backbone, bootstrapped, serverdata, appBase) {
    var Galaxy = {
        root: "/"
    };

    window.Galaxy = Galaxy;

    $("head").append(
        $('<link rel="stylesheet" type="text/css"  />').attr("href", "/base/galaxy/scripts/qunit/assets/base.css")
    );

    appBase = appBase.default;
    return {
        create: function() {
            window.Galaxy = new appBase.GalaxyApp(bootstrapped);
            window.Galaxy.currHistoryPanel = { model: new Backbone.Model() };
            window.Galaxy.emit = {
                debug: function() {},
                error: function(v) {
                    window.console.error(v);
                }
            };
            window.WAIT_FADE = 300;
            window.fakeserver = sinon.fakeServer.create();
            for (var route in serverdata) {
                window.fakeserver.respondWith("GET", window.Galaxy.root + route, [
                    200,
                    { "Content-Type": "application/json" },
                    serverdata[route].data
                ]);
            }
        },
        destroy: function() {
            if (window.fakeserver) {
                window.fakeserver.restore();
                delete window.fakeserver;
            }
        }
    };
});
