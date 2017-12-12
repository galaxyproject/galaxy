define("mvc/user/user-model", ["exports", "libs/underscore", "libs/backbone", "mvc/base-mvc", "utils/localization"], function(exports, _underscore, _backbone, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _ = _interopRequireWildcard(_underscore);

    var Backbone = _interopRequireWildcard(_backbone);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    function _interopRequireWildcard(obj) {
        if (obj && obj.__esModule) {
            return obj;
        } else {
            var newObj = {};

            if (obj != null) {
                for (var key in obj) {
                    if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key];
                }
            }

            newObj.default = obj;
            return newObj;
        }
    }

    var logNamespace = "user";
    //==============================================================================
    /** @class Model for a Galaxy user (including anonymous users).
     *  @name User
     */
    var User = Backbone.Model.extend(_baseMvc2.default.LoggableMixin).extend(
        /** @lends User.prototype */
        {
            _logNamespace: logNamespace,

            /** API location for this resource */
            urlRoot: function urlRoot() {
                return Galaxy.root + "api/users";
            },

            /** Model defaults
             *  Note: don't check for anon-users with the username as the default is '(anonymous user)'
             *      a safer method is if( !user.get( 'email' ) ) -> anon user
             */
            defaults: /** @lends User.prototype */ {
                id: null,
                username: "(" + (0, _localization2.default)("anonymous user") + ")",
                email: "",
                total_disk_usage: 0,
                nice_total_disk_usage: "",
                quota_percent: null,
                is_admin: false
            },

            /** Set up and bind events
             *  @param {Object} data Initial model data.
             */
            initialize: function initialize(data) {
                this.log("User.initialize:", data);

                this.on("loaded", function(model, resp) {
                    this.log(this + " has loaded:", model, resp);
                });
                this.on("change", function(model, data) {
                    this.log(this + " has changed:", model, data.changes);
                });
            },

            isAnonymous: function isAnonymous() {
                return !this.get("email");
            },

            isAdmin: function isAdmin() {
                return this.get("is_admin");
            },

            /** Load a user with the API using an id.
             *      If getting an anonymous user or no access to a user id, pass the User.CURRENT_ID_STR
             *      (e.g. 'current') and the API will return the current transaction's user data.
             *  @param {String} idOrCurrent encoded user id or the User.CURRENT_ID_STR
             *  @param {Object} options hash to pass to Backbone.Model.fetch. Can contain success, error fns.
             *  @fires loaded when the model has been loaded from the API, passing the newModel and AJAX response.
             */
            loadFromApi: function loadFromApi(idOrCurrent, options) {
                idOrCurrent = idOrCurrent || User.CURRENT_ID_STR;

                options = options || {};
                var model = this;
                var userFn = options.success;

                /** @ignore */
                options.success = function(newModel, response) {
                    model.trigger("loaded", newModel, response);
                    if (userFn) {
                        userFn(newModel, response);
                    }
                };

                // requests for the current user must have a sep. constructed url (fetch don't work, ma)
                if (idOrCurrent === User.CURRENT_ID_STR) {
                    options.url = this.urlRoot + "/" + User.CURRENT_ID_STR;
                }
                return Backbone.Model.prototype.fetch.call(this, options);
            },

            /** Clears all data from the sessionStorage.
             */
            clearSessionStorage: function clearSessionStorage() {
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
            toString: function toString() {
                var userInfo = [this.get("username")];
                if (this.get("id")) {
                    userInfo.unshift(this.get("id"));
                    userInfo.push(this.get("email"));
                }
                return "User(" + userInfo.join(":") + ")";
            }
        });

    // string to send to tell server to return this transaction's user (see api/users.py)
    User.CURRENT_ID_STR = "current";

    // class method to load the current user via the api and return that model
    User.getCurrentUserFromApi = function(options) {
        var currentUser = new User();
        currentUser.loadFromApi(User.CURRENT_ID_STR, options);
        return currentUser;
    };

    // (stub) collection for users (shouldn't be common unless admin UI)
    var UserCollection = Backbone.Collection.extend(_baseMvc2.default.LoggableMixin).extend({
        model: User,
        urlRoot: function urlRoot() {
            return Galaxy.root + "api/users";
        }
        //logger  : console,
    });

    //==============================================================================
    exports.default = {
        User: User
    };
});
//# sourceMappingURL=../../../maps/mvc/user/user-model.js.map
