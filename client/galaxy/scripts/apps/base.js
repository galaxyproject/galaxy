import $ from "jquery";
import "bootstrap";
import * as _ from "underscore";
import GalaxyApp from "galaxy";
import Page from "layout/page";

/* global Galaxy */
window.app = function app(options, bootstrapped) {
    window.Galaxy = new GalaxyApp.GalaxyApp(options, bootstrapped);
    Galaxy.debug("base app");
    $(() => {
        options.config = _.extend(options.config, {
            hide_panels: Galaxy.params.hide_panels,
            hide_masthead: Galaxy.params.hide_masthead
        });
        Galaxy.page = new Page.View(options);
        alert('here');
    });
};
