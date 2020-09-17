import jQuery from "jquery";
("use_strict");

var $ = jQuery;
//=============================================================================

jQuery.fn.extend({
    hoverhighlight: function $hoverhighlight(scope, color) {
        scope = scope || "body";
        if (!this.length) {
            return this;
        }

        $(this).each(function () {
            var $this = $(this);
            var targetSelector = $this.data("target");

            if (targetSelector) {
                $this
                    .mouseover((ev) => {
                        $(targetSelector, scope).css({
                            background: color,
                        });
                    })
                    .mouseout((ev) => {
                        $(targetSelector).css({
                            background: "",
                        });
                    });
            }
        });
        return this;
    },
});
