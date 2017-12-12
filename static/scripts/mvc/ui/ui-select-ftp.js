define("mvc/ui/ui-select-ftp", ["exports", "utils/utils", "mvc/ui/ui-list"], function(exports, _utils, _uiList) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    var _uiList2 = _interopRequireDefault(_uiList);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /**
     * FTP file selector
     */
    // dependencies
    var View = Backbone.View.extend({
        // initialize
        initialize: function initialize(options) {
            // link this
            var self = this;

            // create ui-list view to keep track of selected ftp files
            this.ftpfile_list = new _uiList2.default.View({
                name: "file",
                optional: options.optional,
                multiple: options.multiple,
                onchange: function onchange() {
                    options.onchange && options.onchange(self.value());
                }
            });

            // create elements
            this.setElement(this.ftpfile_list.$el);

            // initial fetch of ftps
            _utils2.default.get({
                url: Galaxy.root + "api/remote_files",
                success: function success(response) {
                    var data = [];
                    for (var i in response) {
                        data.push({
                            value: response[i]["path"],
                            label: response[i]["path"]
                        });
                    }
                    self.ftpfile_list.update(data);
                }
            });
        },

        /** Return/Set currently selected ftp datasets */
        value: function value(val) {
            return this.ftpfile_list.value(val);
        }
    });

    exports.default = {
        View: View
    };
});
//# sourceMappingURL=../../../maps/mvc/ui/ui-select-ftp.js.map
