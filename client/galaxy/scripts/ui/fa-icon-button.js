import jQuery from "jquery";
import * as _ from "underscore";
("use_strict");

var $ = jQuery;
//============================================================================
/** Returns a jQuery object containing a clickable font-awesome button.
 *      options:
 *          tooltipConfig   : option map for bootstrap tool tip
 *          classes         : array of class names (will always be classed as icon-btn)
 *          disabled        : T/F - add the 'disabled' class?
 *          title           : tooltip/title string
 *          target          : optional href target
 *          href            : optional href
 *          faIcon          : which font awesome icon to use
 *          onclick         : function to call when the button is clicked
 */
var faIconButton = options => {
    options = options || {};
    options.tooltipConfig = options.tooltipConfig || {
        placement: "bottom"
    };

    options.classes = ["icon-btn"].concat(options.classes || []);
    if (options.disabled) {
        options.classes.push("disabled");
    }

    var html = [
        '<a class="',
        options.classes.join(" "),
        '"',
        options.title ? ` title="${options.title}"` : "",
        !options.disabled && options.target ? ` target="${options.target}"` : "",
        ' href="',
        !options.disabled && options.href ? options.href : "javascript:void(0);",
        '">',
        // could go with something less specific here - like 'html'
        '<span class="fa ',
        options.faIcon,
        '"></span>',
        "</a>"
    ].join("");
    var $button = $(html).tooltip(options.tooltipConfig);
    if (_.isFunction(options.onclick)) {
        let wrapped = _.wrap(options.onclick, function(func) {
            $button.tooltip("hide");
            func.apply(this, arguments);
        });
        $button.click(wrapped);
    }
    return $button;
};

//============================================================================
export default faIconButton;
