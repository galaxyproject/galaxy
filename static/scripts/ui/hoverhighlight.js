define("ui/hoverhighlight", ["jquery"], function(_jquery) {
    "use strict";

    var _jquery2 = _interopRequireDefault(_jquery);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    "use_strict";

    var $ = _jquery2.default;
    //=============================================================================

    _jquery2.default.fn.extend({
        hoverhighlight: function $hoverhighlight(scope, color) {
            scope = scope || "body";
            if (!this.length) {
                return this;
            }

            $(this).each(function() {
                var $this = $(this);
                var targetSelector = $this.data("target");

                if (targetSelector) {
                    $this.mouseover(function(ev) {
                        $(targetSelector, scope).css({
                            background: color
                        });
                    }).mouseout(function(ev) {
                        $(targetSelector).css({
                            background: ""
                        });
                    });
                }
            });
            return this;
        }
    });
});
//# sourceMappingURL=../../maps/ui/hoverhighlight.js.map
