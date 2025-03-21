import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";

//==============================================================================
/** @class Model for a Galaxy user (including anonymous users).
 *  @name User
 */
var User = Backbone.Model.extend(
    /** @lends User.prototype */ {
        /** API location for this resource */
        urlRoot: function () {
            return `${getAppRoot()}api/users`;
        },

        /** Model defaults
         *  Note: don't check for anon-users with the username as the default is '(anonymous user)'
         *      a safer method is if( !user.get( 'email' ) ) -> anon user
         */
        defaults: /** @lends User.prototype */ {
            id: null,
            username: `(${_l("匿名用户")})`,
            email: "",
            total_disk_usage: 0,
            nice_total_disk_usage: "",
            quota_percent: null,
            is_admin: false,
            preferences: {},
        },

        /** Set up and bind events
         *  @param {Object} data Initial model data.
         */
        initialize: function (data) {
            this.on("loaded", function (model, resp) {
                console.log(`${this} has loaded:`, model, resp);
            });
            this.on("change", function (model, data) {
                console.log(`${this} has changed:`, model, data.changes);
            });
        },

        isAnonymous: function () {
            return !this.get("email");
        },

        isAdmin: function () {
            return this.get("is_admin");
        },

        updatePreferences: function (name, new_value) {
            const preferences = this.get("preferences");
            preferences[name] = JSON.stringify(new_value);
            this.preferences = preferences;
        },

        getFavorites: function () {
            const preferences = this.get("preferences");
            if (preferences && preferences.favorites) {
                return JSON.parse(preferences.favorites);
            } else {
                return {
                    tools: [],
                };
            }
        },

        updateFavorites: function (object_type, new_favorites) {
            const favorites = this.getFavorites();
            favorites[object_type] = new_favorites[object_type];
            this.updatePreferences("favorites", favorites);
        },

        /** Load a user with the API using an id.
         *      If getting an anonymous user or no access to a user id, pass the User.CURRENT_ID_STR
         *      (e.g. 'current') and the API will return the current transaction's user data.
         *  @param {String} idOrCurrent encoded user id or the User.CURRENT_ID_STR
         *  @param {Object} options hash to pass to Backbone.Model.fetch. Can contain success, error fns.
         *  @fires loaded when the model has been loaded from the API, passing the newModel and AJAX response.
         */
        loadFromApi: function (idOrCurrent, options) {
            idOrCurrent = idOrCurrent || User.CURRENT_ID_STR;

            options = options || {};
            var model = this;
            var userFn = options.success;

            /** @ignore */
            options.success = (newModel, response) => {
                model.trigger("loaded", newModel, response);
                if (userFn) {
                    userFn(newModel, response);
                }
            };

            // requests for the current user must have a sep. constructed url (fetch don't work, ma)
            if (idOrCurrent === User.CURRENT_ID_STR) {
                options.url = `${this.urlRoot}/${User.CURRENT_ID_STR}`;
            }
            return Backbone.Model.prototype.fetch.call(this, options);
        },

        /** Clears all data from the sessionStorage.
         */
        clearSessionStorage: function () {
            for (var key in sessionStorage) {
                //TODO: store these under the user key so we don't have to do this
                // currently only history
                if (key.indexOf("history:") === 0) {
                    sessionStorage.removeItem(key);
                } else if (key === "history-panel") {
                    sessionStorage.removeItem(key);
                }
            }
        },

        /** string representation */
        toString: function () {
            var userInfo = [this.get("username")];
            if (this.get("id")) {
                userInfo.unshift(this.get("id"));
                userInfo.push(this.get("email"));
            }
            return `User(${userInfo.join(":")})`;
        },
    }
);

// string to send to tell server to return this transaction's user (see api/users.py)
User.CURRENT_ID_STR = "current";

// class method to load the current user via the api and return that model
User.getCurrentUserFromApi = (options) => {
    var currentUser = new User();
    currentUser.loadFromApi(User.CURRENT_ID_STR, options);
    return currentUser;
};

//==============================================================================
export default {
    User: User,
};
