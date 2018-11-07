/** Creates a generic/global Galaxy environment, loads shared libraries and a
 * fake server */

import sinon from "sinon";
import Backbone from "backbone";
import { setGalaxyInstance } from "app";
import galaxyOptions from "qunit/test-data/bootstrapped";
import serverdata from "qunit/test-data/fakeserver";
import "./assets/base.css";

export default {

    create() {

        setGalaxyInstance((GalaxyApp) => {
            console.log("setting default galaxy", galaxyOptions);
            let galaxy = new GalaxyApp(galaxyOptions);
            galaxy.currHistoryPanel = { 
                model: new Backbone.Model()
            };
            galaxy.emit = {
                debug: function() {},
                error: function(v) {
                    window.console.error(v);
                }
            };
            return galaxy;
        });

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

    destroy() {
        if (window.fakeserver) {
            window.fakeserver.restore();
            delete window.fakeserver;
        }
    }
}
