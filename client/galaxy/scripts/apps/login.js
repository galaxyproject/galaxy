import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import _l from "utils/localization";
import Page from "layout/page";
import { setGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";

window.app = function app(options, bootstrapped) {
    console.log("Analysis init");

    let Galaxy = setGalaxyInstance(GalaxyApp => {
        let galaxy = new GalaxyApp(options, bootstrapped);
        galaxy.debug("login app");
        return galaxy;
    });

    var redirect = encodeURI(options.redirect);

    // TODO: remove iframe for user login (at least) and render login page from here
    // then remove this redirect
    if (!options.show_welcome_with_login) {
        var params = $.param({ use_panels: "True", redirect: redirect });
        window.location.href = `${getAppRoot()}user/login?${params}`;
        return;
    }

    var LoginPage = Backbone.View.extend({
        initialize: function(page) {
            this.page = page;
            this.model = new Backbone.Model({ title: _l("Login required") });
            this.setElement(this._template());
        },
        render: function() {
            this.page.$("#galaxy_main").prop("src", options.welcome_url);
        },
        _template: function() {
            var login_url = `${options.root}user/login?${$.param({
                redirect: redirect
            })}`;
            return `<iframe src="${login_url}" frameborder="0" style="width: 100%; height: 100%;"/>`;
        }
    });

    $(() => {
        Galaxy.page = new Page.View(
            _.extend(options, {
                Right: LoginPage
            })
        );
    });
};
