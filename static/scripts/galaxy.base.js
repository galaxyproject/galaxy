function obj_length(obj) {
    if (void 0 !== obj.length) return obj.length;
    var count = 0;
    for (var element in obj) count++;
    return count;
}

function make_popupmenu(button_element, initial_options) {
    var element_menu_exists = button_element.data("menu_options");
    button_element.data("menu_options", initial_options), element_menu_exists || button_element.bind("click.show_popup", function(e) {
        return $(".popmenu-wrapper").remove(), setTimeout(function() {
            var menu_element = $("<ul class='dropdown-menu' id='" + button_element.attr("id") + "-menu'></ul>"), options = button_element.data("menu_options");
            obj_length(options) <= 0 && $("<li>No Options.</li>").appendTo(menu_element), $.each(options, function(k, v) {
                if (v) {
                    var action = v.action || v;
                    menu_element.append($("<li></li>").append($("<a>").attr("href", v.url).html(k).click(action)));
                } else menu_element.append($("<li></li>").addClass("head").append($("<a href='#'></a>").html(k)));
            });
            var wrapper = $("<div class='popmenu-wrapper' style='position: absolute;left: 0; top: -1000;'></div>").append(menu_element).appendTo("body"), x = e.pageX - wrapper.width() / 2;
            x = Math.min(x, $(document).scrollLeft() + $(window).width() - $(wrapper).width() - 5), 
            x = Math.max(x, $(document).scrollLeft() + 5), wrapper.css({
                top: e.pageY,
                left: x
            });
        }, 10), setTimeout(function() {
            var close_popup = function(el) {
                $(el).bind("click.close_popup", function() {
                    $(".popmenu-wrapper").remove(), el.unbind("click.close_popup");
                });
            };
            close_popup($(window.document)), close_popup($(window.top.document));
            for (var frame_id = window.top.frames.length; frame_id--; ) {
                var frame = $(window.top.frames[frame_id].document);
                close_popup(frame);
            }
        }, 50), !1;
    });
}

function make_popup_menus(parent) {
    parent = parent || document, $(parent).find("div[popupmenu]").each(function() {
        var options = {}, menu = $(this);
        menu.find("a").each(function() {
            var link = $(this), link_dom = link.get(0), confirmtext = link_dom.getAttribute("confirm"), href = link_dom.getAttribute("href"), target = link_dom.getAttribute("target");
            options[link.text()] = href ? {
                url: href,
                action: function(event) {
                    if (!confirmtext || confirm(confirmtext)) {
                        if (target) return window.open(href, target), !1;
                        link.click();
                    } else event.preventDefault();
                }
            } : null;
        });
        var box = $(parent).find("#" + menu.attr("popupmenu"));
        box.find("a").bind("click", function(e) {
            return e.stopPropagation(), !0;
        }), make_popupmenu(box, options), box.addClass("popup"), menu.remove();
    });
}

function replace_big_select_inputs(min_length, max_length, select_elts) {
    jQuery.fn.select2 && (void 0 === min_length && (min_length = 20), void 0 === max_length && (max_length = 3e3), 
    select_elts = select_elts || $("select"), select_elts.each(function() {
        var select_elt = $(this).not("[multiple]"), num_options = select_elt.find("option").length;
        min_length > num_options || num_options > max_length || select_elt.hasClass("no-autocomplete") || select_elt.refresh_select2();
    }));
}

function async_save_text(click_to_edit_elt, text_elt_id, save_url, text_parm_name, num_cols, use_textarea, num_rows, on_start, on_finish) {
    void 0 === num_cols && (num_cols = 30), void 0 === num_rows && (num_rows = 4), $("#" + click_to_edit_elt).click(function() {
        if (!($("#renaming-active").length > 0)) {
            var t, text_elt = $("#" + text_elt_id), old_text = text_elt.text();
            t = use_textarea ? $("<textarea></textarea>").attr({
                rows: num_rows,
                cols: num_cols
            }).text($.trim(old_text)) : $("<input type='text'></input>").attr({
                value: $.trim(old_text),
                size: num_cols
            }), t.attr("id", "renaming-active"), t.blur(function() {
                $(this).remove(), text_elt.show(), on_finish && on_finish(t);
            }), t.keyup(function(e) {
                if (27 === e.keyCode) $(this).trigger("blur"); else if (13 === e.keyCode) {
                    var ajax_data = {};
                    ajax_data[text_parm_name] = $(this).val(), $(this).trigger("blur"), $.ajax({
                        url: save_url,
                        data: ajax_data,
                        error: function() {
                            alert("Text editing for elt " + text_elt_id + " failed");
                        },
                        success: function(processed_text) {
                            "" !== processed_text ? text_elt.text(processed_text) : text_elt.html("<em>None</em>"), 
                            on_finish && on_finish(t);
                        }
                    });
                }
            }), on_start && on_start(t), text_elt.hide(), t.insertAfter(text_elt), t.focus(), 
            t.select();
        }
    });
}

function commatize(number) {
    number += "";
    for (var rgx = /(\d+)(\d{3})/; rgx.test(number); ) number = number.replace(rgx, "$1,$2");
    return number;
}

function reset_tool_search(initValue) {
    var tool_menu_frame = $("#galaxy_tools").contents();
    if (0 === tool_menu_frame.length && (tool_menu_frame = $(document)), $(this).removeClass("search_active"), 
    tool_menu_frame.find(".toolTitle").removeClass("search_match"), tool_menu_frame.find(".toolSectionBody").hide(), 
    tool_menu_frame.find(".toolTitle").show(), tool_menu_frame.find(".toolPanelLabel").show(), 
    tool_menu_frame.find(".toolSectionWrapper").each(function() {
        "recently_used_wrapper" !== $(this).attr("id") ? $(this).show() : $(this).hasClass("user_pref_visible") && $(this).show();
    }), tool_menu_frame.find("#search-no-results").hide(), tool_menu_frame.find("#search-spinner").hide(), 
    initValue) {
        var search_input = tool_menu_frame.find("#tool-search-query");
        search_input.val("search tools");
    }
}

function init_refresh_on_change() {
    $("select[refresh_on_change='true']").off("change").change(function() {
        var select_field = $(this), select_val = select_field.val(), ref_on_change_vals = select_field.attr("refresh_on_change_values");
        if (ref_on_change_vals) {
            ref_on_change_vals = ref_on_change_vals.split(",");
            var last_selected_value = select_field.attr("last_selected_value");
            if (-1 === $.inArray(select_val, ref_on_change_vals) && -1 === $.inArray(last_selected_value, ref_on_change_vals)) return;
        }
        $(window).trigger("refresh_on_change"), $(document).trigger("convert_to_values"), 
        select_field.get(0).form.submit();
    }), $(":checkbox[refresh_on_change='true']").off("click").click(function() {
        var select_field = $(this), select_val = select_field.val(), ref_on_change_vals = select_field.attr("refresh_on_change_values");
        if (ref_on_change_vals) {
            ref_on_change_vals = ref_on_change_vals.split(",");
            var last_selected_value = select_field.attr("last_selected_value");
            if (-1 === $.inArray(select_val, ref_on_change_vals) && -1 === $.inArray(last_selected_value, ref_on_change_vals)) return;
        }
        $(window).trigger("refresh_on_change"), select_field.get(0).form.submit();
    }), $("a[confirm]").off("click").click(function() {
        return confirm($(this).attr("confirm"));
    });
}

!function() {
    for (var lastTime = 0, vendors = [ "ms", "moz", "webkit", "o" ], x = 0; x < vendors.length && !window.requestAnimationFrame; ++x) window.requestAnimationFrame = window[vendors[x] + "RequestAnimationFrame"], 
    window.cancelRequestAnimationFrame = window[vendors[x] + "CancelRequestAnimationFrame"];
    window.requestAnimationFrame || (window.requestAnimationFrame = function(callback) {
        var currTime = new Date().getTime(), timeToCall = Math.max(0, 16 - (currTime - lastTime)), id = window.setTimeout(function() {
            callback(currTime + timeToCall);
        }, timeToCall);
        return lastTime = currTime + timeToCall, id;
    }), window.cancelAnimationFrame || (window.cancelAnimationFrame = function(id) {
        clearTimeout(id);
    });
}(), Array.indexOf || (Array.prototype.indexOf = function(obj) {
    for (var i = 0, len = this.length; len > i; i++) if (this[i] == obj) return i;
    return -1;
}), $.fn.makeAbsolute = function(rebase) {
    return this.each(function() {
        var el = $(this), pos = el.position();
        el.css({
            position: "absolute",
            marginLeft: 0,
            marginTop: 0,
            top: pos.top,
            left: pos.left,
            right: $(window).width() - (pos.left + el.width())
        }), rebase && el.remove().appendTo("body");
    });
}, $.fn.refresh_select2 = function() {
    var select_elt = $(this), options = {
        placeholder: "Click to select",
        closeOnSelect: !select_elt.is("[MULTIPLE]"),
        dropdownAutoWidth: !0,
        containerCssClass: "select2-minwidth"
    };
    return select_elt.select2(options);
}, $.fn.make_text_editable = function(config_dict) {
    var num_cols = "num_cols" in config_dict ? config_dict.num_cols : 30, num_rows = "num_rows" in config_dict ? config_dict.num_rows : 4, use_textarea = "use_textarea" in config_dict ? config_dict.use_textarea : !1, on_finish = "on_finish" in config_dict ? config_dict.on_finish : null, help_text = "help_text" in config_dict ? config_dict.help_text : null, container = $(this);
    return container.addClass("editable-text").click(function(e) {
        if (!($(this).children(":input").length > 0)) {
            container.removeClass("editable-text");
            var input_elt, button_elt, set_text = function(new_text) {
                container.find(":input").remove(), "" !== new_text ? container.text(new_text) : container.html("<br>"), 
                container.addClass("editable-text"), on_finish && on_finish(new_text);
            }, cur_text = "cur_text" in config_dict ? config_dict.cur_text : container.text();
            use_textarea ? (input_elt = $("<textarea/>").attr({
                rows: num_rows,
                cols: num_cols
            }).text($.trim(cur_text)).keyup(function(e) {
                27 === e.keyCode && set_text(cur_text);
            }), button_elt = $("<button/>").text("Done").click(function() {
                return set_text(input_elt.val()), !1;
            })) : input_elt = $("<input type='text'/>").attr({
                value: $.trim(cur_text),
                size: num_cols
            }).blur(function() {
                set_text(cur_text);
            }).keyup(function(e) {
                27 === e.keyCode ? $(this).trigger("blur") : 13 === e.keyCode && set_text($(this).val()), 
                e.stopPropagation();
            }), container.text(""), container.append(input_elt), button_elt && container.append(button_elt), 
            input_elt.focus(), input_elt.select(), e.stopPropagation();
        }
    }), help_text && container.attr("title", help_text).tooltip(), container;
};

var GalaxyAsync = function(log_action) {
    this.url_dict = {}, this.log_action = void 0 === log_action ? !1 : log_action;
};

GalaxyAsync.prototype.set_func_url = function(func_name, url) {
    this.url_dict[func_name] = url;
}, GalaxyAsync.prototype.set_user_pref = function(pref_name, pref_value) {
    var url = this.url_dict[arguments.callee];
    return void 0 === url ? !1 : void $.ajax({
        url: url,
        data: {
            pref_name: pref_name,
            pref_value: pref_value
        },
        error: function() {
            return !1;
        },
        success: function() {
            return !0;
        }
    });
}, GalaxyAsync.prototype.log_user_action = function(action, context, params) {
    if (this.log_action) {
        var url = this.url_dict[arguments.callee];
        return void 0 === url ? !1 : void $.ajax({
            url: url,
            data: {
                action: action,
                context: context,
                params: params
            },
            error: function() {
                return !1;
            },
            success: function() {
                return !0;
            }
        });
    }
}, jQuery.fn.preventDoubleSubmission = function() {
    return $(this).on("submit", function(e) {
        var $form = $(this);
        $form.data("submitted") === !0 ? e.preventDefault() : $form.data("submitted", !0);
    }), this;
}, $(document).ready(function() {
    init_refresh_on_change(), $.fn.tooltip && ($(".unified-panel-header [title]").tooltip({
        placement: "bottom"
    }), $("[title]").tooltip()), make_popup_menus(), replace_big_select_inputs(20, 1500), 
    $("a").click(function() {
        var anchor = $(this), galaxy_main_exists = parent.frames && parent.frames.galaxy_main;
        if ("galaxy_main" == anchor.attr("target") && !galaxy_main_exists) {
            var href = anchor.attr("href");
            href += -1 == href.indexOf("?") ? "?" : "&", href += "use_panels=True", anchor.attr("href", href), 
            anchor.attr("target", "_self");
        }
        return anchor;
    });
}), window.obj_length = obj_length, window.make_popupmenu = make_popupmenu, window.make_popup_menus = make_popup_menus, 
window.replace_big_select_inputs = replace_big_select_inputs, window.async_save_text = async_save_text, 
window.commatize = commatize, window.reset_tool_search = reset_tool_search, window.GalaxyAsync = GalaxyAsync, 
window.init_refresh_on_change = init_refresh_on_change;