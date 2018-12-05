import _l from "utils/localization";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload";

export const getLoginPage = options => {
    let rootUrl = getAppRoot();
    let redirect = encodeURI(options.redirect);

    return Backbone.View.extend({
        initialize: function(page) {
            this.page = page;
            this.model = new Backbone.Model({ title: _l("Login required") });
            this.setElement(this._template());
        },
        render: function() {
            this.page.$("#galaxy_main").prop("src", options.welcome_url);
        },
        _template: function() {
            var login_url = `${rootUrl}user/login?${$.param({
                redirect: redirect
            })}`;
            return `<iframe src="${login_url}" frameborder="0" style="width: 100%; height: 100%;"/>`;
        }
    });
};
