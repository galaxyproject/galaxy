import jQuery from "jquery";
("use_strict");

var $ = jQuery;
//TODO: too specific to history panel
function LoadingIndicator($where, options) {
    var self = this;
    // defaults
    options = jQuery.extend(
        {
            cover: false,
        },
        options || {}
    );

    function render() {
        var html = [
            '<div class="loading-indicator">',
            '<div class="loading-indicator-text">',
            '<span class="fa fa-spinner fa-spin fa-lg"></span>',
            '<span class="loading-indicator-message">loading...</span>',
            "</div>",
            "</div>",
        ].join("\n");

        var $indicator = $(html)
            .hide()
            .css(
                options.css || {
                    position: "fixed",
                }
            );

        var $text = $indicator.children(".loading-indicator-text");

        if (options.cover) {
            $indicator.css({
                "z-index": 2,
                top: $where.css("top"),
                bottom: $where.css("bottom"),
                left: $where.css("left"),
                right: $where.css("right"),
                opacity: 0.5,
                "background-color": "white",
                "text-align": "center",
            });
            $text = $indicator.children(".loading-indicator-text").css({
                "margin-top": "20px",
            });
        } else {
            $text = $indicator.children(".loading-indicator-text").css({
                margin: "12px 0px 0px 10px",
                opacity: "0.85",
                color: "grey",
            });
            $text.children(".loading-indicator-message").css({
                margin: "0px 8px 0px 0px",
                "font-style": "italic",
            });
        }
        return $indicator;
    }

    self.show = (msg, speed, callback) => {
        msg = msg || "loading...";
        speed = speed || "fast";
        // remove previous
        $where.parent().find(".loading-indicator").remove();
        // since position is fixed - we insert as sibling
        self.$indicator = render().insertBefore($where);
        self.message(msg);
        self.$indicator.fadeIn(speed, callback);
        return self;
    };

    self.message = (msg) => {
        self.$indicator.find("i").text(msg);
    };

    self.hide = (speed, callback) => {
        speed = speed || "fast";
        if (self.$indicator && self.$indicator.length) {
            self.$indicator.fadeOut(speed, () => {
                self.$indicator.remove();
                if (callback) {
                    callback();
                }
            });
        } else {
            if (callback) {
                callback();
            }
        }
        return self;
    };
    return self;
}

const markViewAsLoading = function (view) {
    view.setElement($('<div><div class="loading"></div></div>'));
    new LoadingIndicator(view.$(".loading")).show();
};

//============================================================================
export default {
    LoadingIndicator: LoadingIndicator,
    markViewAsLoading: markViewAsLoading,
};
