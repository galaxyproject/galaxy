import jQuery from "jquery";
("use_strict");

var $ = jQuery;
var _l = window._l || ((s) => s);

//TODO: consolidate with tool menu functionality, use there

/** searchInput: (jQuery plugin)
 *      Creates a search input, a clear button, and loading indicator
 *      within the selected node.
 *
 *      When the user either presses return or enters some minimal number
 *      of characters, a callback is called. Pressing ESC when the input
 *      is focused will clear the input and call a separate callback.
 */
function searchInput(parentNode, options) {
    var KEYCODE_ESC = 27;
    var KEYCODE_RETURN = 13;
    var $parentNode = $(parentNode);
    var firstSearch = true;

    var defaults = {
        initialVal: "",
        name: "search",
        placeholder: "search",
        classes: "",
        onclear: function () {},
        onfirstsearch: null,
        onsearch: function (inputVal) {},
        minSearchLen: 0,
        escWillClear: true,
        advsearchlink: false,
        oninit: function () {},
    };

    // .................................................................... input rendering and events
    // visually clear the search, trigger an event, and call the callback
    function clearSearchInput(event) {
        var $input = $(this).closest(".search-control").children("input");
        $input.val("").trigger("searchInput.clear").blur();
        options.onclear();
    }

    // search for searchTerms, trigger an event, call the appropo callback (based on whether this is the first)
    function search(event, searchTerms) {
        if (!searchTerms) {
            return clearSearchInput();
        }
        $(this).trigger("search.search", searchTerms);
        if (typeof options.onfirstsearch === "function" && firstSearch) {
            firstSearch = false;
            options.onfirstsearch(searchTerms);
        } else {
            options.onsearch(searchTerms);
        }
    }

    // .................................................................... input rendering and events
    function inputTemplate() {
        // class search-query is bootstrap 2.3 style that now lives in base.less
        return [
            '<input type="text" name="',
            options.name,
            '" placeholder="',
            options.placeholder,
            '" ',
            'class="search-query ',
            options.classes,
            '" ',
            "/>",
        ].join("");
    }

    // the search input that responds to keyboard events and displays the search value
    function $input() {
        return (
            $(inputTemplate())
                // select all text on a focus
                .focus(function (event) {
                    $(this).select();
                })
                // attach behaviors to esc, return if desired, search on some min len string
                .keyup(function (event) {
                    event.preventDefault();
                    event.stopPropagation();

                    // esc key will clear if desired
                    if (event.which === KEYCODE_ESC && options.escWillClear) {
                        clearSearchInput.call(this, event);
                    } else {
                        var searchTerms = $(this).val();
                        // return key or the search string len > minSearchLen (if not 0) triggers search
                        if (
                            event.which === KEYCODE_RETURN ||
                            (options.minSearchLen && searchTerms.length >= options.minSearchLen)
                        ) {
                            search.call(this, event, searchTerms);
                        }
                    }
                })
                .val(options.initialVal)
        );
    }

    // .................................................................... clear button rendering and events
    // a button for clearing the search bar, placed on the right hand side
    function $clearBtn() {
        return $(
            ['<span class="search-clear fa fa-times-circle" ', 'title="', _l("clear search (esc)"), '"></span>'].join(
                ""
            )
        )
            .tooltip({ placement: "bottom" })
            .click(function (event) {
                clearSearchInput.call(this, event);
            });
    }

    //advanced Search popover
    function $advancedSearchPopover() {
        return $(
            [
                '<a tabindex="0" ',
                'class="search-advanced fa fa-question-circle" ',
                'data-toggle="advSearchPopover" ',
                'data-placement="bottom" ',
                'data-content="',
                _l(
                    "<p>You can use advanced searches here using keywords and syntax like <em>name=mydataset</em> or <em>state=error</em>."
                ),
                "<br/>",
                _l(
                    "Supported keywords are <em>name, format, database, annotation, description, info, tag, hid, state, and history_content_type</em>."
                ),
                "<br/>",
                _l("To learn more visit "),
                "<a href='https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/history/tutorial.html#basic-searching' target='_blank'>",
                _l("the Training Material"),
                '.</a></p>" title="',
                _l("Search tips"),
                '"></a>',
            ].join("")
        )
            .tooltip({ placement: "top", trigger: "hover" })
            .click(function () {
                $(this)
                    .popover({
                        html: true,
                        container: "body",
                    })
                    .popover("show");
            });
    }
    // Hack to hide the advanced search popover when clicking outside
    $("body").on("click", function (e) {
        $('[data-toggle="advSearchPopover"]').each(function () {
            if (
                !$(this).is(e.target) &&
                $(this).has(e.target).length === 0 &&
                $(".popover").has(e.target).length === 0
            ) {
                $(this).popover("hide");
            }
        });
    });

    // .................................................................... loadingIndicator rendering
    // a button for clearing the search bar, placed on the right hand side
    function $loadingIndicator() {
        return $(
            ['<span class="search-loading fa fa-spinner fa-spin" ', 'title="', _l("loading..."), '"></span>'].join("")
        )
            .hide()
            .tooltip({ placement: "bottom" });
    }

    // .................................................................... commands
    // visually swap the load, clear buttons
    function toggleLoadingIndicator() {
        $parentNode.find(".search-loading").toggle();
        $parentNode.find(".search-clear").toggle();
    }

    // .................................................................... init
    // string command (not constructor)
    if (jQuery.type(options) === "string") {
        if (options === "toggle-loading") {
            toggleLoadingIndicator();
        }
        return $parentNode;
    }

    // initial render
    if (jQuery.type(options) === "object") {
        options = jQuery.extend(true, {}, defaults, options);
    }

    var buttonsArr = [$clearBtn(), $loadingIndicator()];
    if (options.advsearchlink) {
        buttonsArr.push($advancedSearchPopover());
    }

    var buttonDiv = $('<div class "search-button-panel"></div>');
    $(buttonDiv).prepend(buttonsArr);

    //NOTE: prepended
    return $parentNode.addClass("search-input").prepend([$input(), $(buttonDiv)]);
}

// as jq plugin
jQuery.fn.extend({
    searchInput: function $searchInput(options) {
        return this.each(function () {
            return searchInput(this, options);
        });
    },
});
