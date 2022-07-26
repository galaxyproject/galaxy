/** Creates a generic/global Galaxy environment, loads shared libraries and a
 * fake server */

// jQuery.fn.tooltip lives on one of these 2 libs
import "bootstrap";

import sinon from "sinon";
import Backbone from "backbone";
import { setGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import galaxyOptions from "./test-data/bootstrapped";
import serverdata from "./test-data/fakeserver";

export function setupTestGalaxy(galaxyOptions_ = null) {
    galaxyOptions_ = galaxyOptions_ || galaxyOptions;
    setGalaxyInstance((GalaxyApp) => {
        const galaxy = new GalaxyApp(galaxyOptions_);
        galaxy.currHistoryPanel = {
            model: new Backbone.Model(),
        };
        galaxy.emit = {
            debug: function () {},
            error: function (v) {
                window.console.error(v);
            },
        };
        return galaxy;
    });
}

export default {
    create() {
        setupTestGalaxy(galaxyOptions);
        window.WAIT_FADE = 300;
        window.fakeserver = sinon.fakeServer.create();
        for (var route in serverdata) {
            window.fakeserver.respondWith("GET", getAppRoot() + route, [
                200,
                { "Content-Type": "application/json" },
                serverdata[route].data,
            ]);
        }
    },

    destroy() {
        if (window.fakeserver) {
            window.fakeserver.restore();
            delete window.fakeserver;
        }
    },
};
