define("layout/router", ["exports", "jquery", "utils/query-string-parsing", "mvc/ui/ui-misc"], function(exports, _jquery, _queryStringParsing, _uiMisc) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _jquery2 = _interopRequireDefault(_jquery);

    var _queryStringParsing2 = _interopRequireDefault(_queryStringParsing);

    var _uiMisc2 = _interopRequireDefault(_uiMisc);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var $ = _jquery2.default;


    var Router = Backbone.Router.extend({
        // TODO: not many client routes at this point - fill and remove from server.
        // since we're at root here, this may be the last to be routed entirely on the client.
        initialize: function initialize(page, options) {
            this.page = page;
            this.options = options;
        },

        /** helper to push a new navigation state */
        push: function push(url, data) {
            data = data || {};
            data.__identifer = Math.random().toString(36).substr(2);
            if (!$.isEmptyObject(data)) {
                url += url.indexOf("?") == -1 ? "?" : "&";
                url += $.param(data, true);
            }
            Galaxy.params = data;
            this.navigate(url, {
                trigger: true
            });
        },

        /** override to parse query string into obj and send to each route */
        execute: function execute(callback, args, name) {
            Galaxy.debug("router execute:", callback, args, name);
            var queryObj = _queryStringParsing2.default.parse(args.pop());
            args.push(queryObj);
            if (callback) {
                if (this.authenticate(args, name)) {
                    callback.apply(this, args);
                } else {
                    this.access_denied();
                }
            }
        },

        authenticate: function authenticate(args, name) {
            return true;
        },

        access_denied: function access_denied() {
            this.page.display(new _uiMisc2.default.Message({
                status: "danger",
                message: "You must be logged in with proper credentials to make this request.",
                persistent: true
            }));
        }
    });

    exports.default = Router;
});
//# sourceMappingURL=../../maps/layout/router.js.map
