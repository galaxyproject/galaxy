import _ from "underscore";
import jQuery from "jquery";
import Backbone from "backbone";

// This is necessary so that, when nested arrays are used in ajax/post/get methods, square brackets ('[]') are
// not appended to the identifier of a nested array.
jQuery.ajaxSettings.traditional = true;

// dependencies
import Utils from "utils/utils";
import GridModel from "legacy/grid/grid-model";
import Templates from "legacy/grid/grid-template";
import PopupMenu from "./popup-menu";
import { init_refresh_on_change } from "onload/globalInits/init_refresh_on_change";

var $ = jQuery;

// grid view
export default Backbone.View.extend({
    // model
    grid: null,

    // Initialize
    initialize: function (grid_config) {
        this.grid = new GridModel();
        this.dict_format = grid_config.dict_format;
        this.title = grid_config.title;
        this.title_id = grid_config.title_id;
        var self = this;

        // why is this a global?
        // Answer: autocom_tagging passes this function from python and
        // it must be on window scope or it won't work.
        // TODO: refactor this out by turning the tagging functionality into a component
        window.add_tag_to_grid_filter = (tag_name, tag_value) => {
            // Put tag name and value together.
            var tag = tag_name + (tag_value !== undefined && tag_value !== "" ? `:${tag_value}` : "");
            var advanced_search = $("#advanced-search").is(":visible");
            if (!advanced_search) {
                $("#standard-search").slideToggle("fast");
                $("#advanced-search").slideToggle("fast");
            }
            self.add_filter_condition("tags", tag);
        };

        // set element
        if (this.dict_format) {
            this.setElement("<div/>");
            if (grid_config.url_base && !grid_config.items) {
                var url_data = grid_config.url_data || {};
                _.each(grid_config.filters, (v, k) => {
                    url_data[`f-${k}`] = v;
                });
                $.ajax({
                    url: `${grid_config.url_base}?${$.param(url_data)}`,
                    success: function (response) {
                        response.embedded = grid_config.embedded;
                        response.filters = grid_config.filters || {};
                        self.init_grid(response);
                    },
                });
            } else {
                this.init_grid(grid_config);
            }
        } else {
            this.setElement("#grid-container");
            this.init_grid(grid_config);
        }

        // fix padding
        if (grid_config.use_panels) {
            $("#center").css({
                padding: "10px",
                overflow: "auto",
            });
        }
    },

    // refresh frames
    handle_refresh: function (refresh_frames) {
        if (refresh_frames) {
            if ($.inArray("history", refresh_frames) > -1) {
                if (window.top.Galaxy && window.top.Galaxy.currHistoryPanel) {
                    window.top.Galaxy.currHistoryPanel.loadCurrentHistory();
                }
            }
        }
    },

    // Initialize
    init_grid: function (grid_config) {
        this.grid.set(grid_config);

        // get options
        var options = this.grid.attributes;

        if (this.allow_title_display && options.title) {
            Utils.setWindowTitle(options.title);
        }
        // handle refresh requests
        this.handle_refresh(options.refresh_frames);

        // strip protocol and domain
        var url = this.grid.get("url_base");
        url = url.replace(/^.*\/\/[^\/]+/, "");
        this.grid.set("url_base", url);

        // append main template
        this.$el.html(Templates.grid(options));

        // update div contents
        this.$el.find("#grid-table-header").html(Templates.header(options));
        this.$el.find("#grid-table-body").html(Templates.body(options));
        this.$el.find("#grid-table-footer").html(Templates.footer(options));

        // update message
        if (options.message) {
            this.$el.find("#grid-message").html(Templates.message(options));
            var self = this;
            if (options.use_hide_message) {
                setTimeout(() => {
                    self.$el.find("#grid-message").html("");
                }, 5000);
            }
        }

        // configure elements
        this.init_grid_elements();
        this.init_grid_controls();

        // attach global event handler
        // TODO: redundant (the onload/standard page handlers do this) - but needed because these are constructed after page ready
        init_refresh_on_change();
    },

    // Initialize grid controls
    init_grid_controls: function () {
        // link
        var self = this;

        // Initialize grid operation button.
        this.$el.find(".operation-button").each(function () {
            $(this).off();
            $(this).click(function () {
                self.submit_operation(this);
                return false;
            });
        });

        // Initialize text filters to select text on click and use normal font when user is typing.
        this.$el.find("input[type=text]").each(function () {
            $(this).off();
            $(this)
                .click(function () {
                    $(this).select();
                })
                .keyup(function () {
                    $(this).css("font-style", "normal");
                });
        });

        // Initialize sort links.
        this.$el.find(".sort-link").each(function () {
            $(this).off();
            $(this).click(function () {
                self.set_sort_condition($(this).attr("sort_key"));
                return false;
            });
        });

        // Initialize text filters.
        this.$el.find(".text-filter-form").each(function () {
            $(this).off();
            $(this).submit(function () {
                var column_key = $(this).attr("column_key");
                var text_input_obj = $(`#input-${column_key}-filter`);
                var text_input = text_input_obj.val();
                text_input_obj.val("");
                self.add_filter_condition(column_key, text_input);
                return false;
            });
        });

        // Initialize categorical filters.
        this.$el.find(".text-filter-val > a").each(function () {
            $(this).off();
            $(this).click(function () {
                // Remove visible element.
                $(this).parent().remove();

                // Remove filter condition.
                self.remove_filter_condition($(this).attr("filter_key"), $(this).attr("filter_val"));

                // Return
                return false;
            });
        });

        // Initialize categorical filters.
        this.$el.find(".categorical-filter > a").each(function () {
            $(this).off();
            $(this).click(function () {
                self.set_categorical_filter($(this).attr("filter_key"), $(this).attr("filter_val"));
                return false;
            });
        });

        // Initialize standard, advanced search toggles.
        this.$el.find(".advanced-search-toggle").each(function () {
            $(this).off();
            $(this).click(() => {
                self.$el.find("#standard-search").slideToggle("fast");
                self.$el.find("#advanced-search").slideToggle("fast");
                return false;
            });
        });

        // Add event to check all box
        this.$el.find("#check_all").off();
        this.$el.find("#check_all").on("click", () => {
            self.check_all_items();
        });
    },

    // Initialize grid elements.
    init_grid_elements: function () {
        // Initialize grid selection checkboxes.
        this.$el.find(".grid").each(function () {
            var checkboxes = $(this).find("input.grid-row-select-checkbox");
            var check_count = $(this).find("span.grid-selected-count");
            var update_checked = () => {
                check_count.text($(checkboxes).filter(":checked").length);
            };

            $(checkboxes).each(function () {
                $(this).change(update_checked);
            });
            update_checked();
        });

        // Initialize ratings.
        if (this.$el.find(".community_rating_star").length !== 0) this.$el.find(".community_rating_star").rating({});

        // get options
        var options = this.grid.attributes;
        var self = this;

        //
        // add page click events
        //
        this.$el.find(".page-link > a").each(function () {
            $(this).click(function () {
                self.set_page($(this).attr("page_num"));
                return false;
            });
        });

        //
        // add inbound/outbound events
        //
        this.$el.find(".use-target").each(function () {
            $(this).click(function () {
                self.execute({
                    href: $(this).attr("href"),
                    target: $(this).attr("target"),
                });
                return false;
            });
        });

        // empty grid?
        var items_length = options.items.length;
        if (items_length === 0) {
            return;
        }

        // add operation popup menus
        _.each(options.items, (item, index) => {
            var button = self.$(`#grid-${item.encode_id}-popup`).off();
            var popup = new PopupMenu(button);
            _.each(options.operations, (operation) => {
                self._add_operation(popup, operation, item);
            });
        });
    },

    /** Add an operation to the items menu */
    _add_operation: function (popup, operation, item) {
        var self = this;
        var settings = item.operation_config[operation.label];
        if (settings.allowed && operation.allow_popup) {
            popup.addItem({
                html: operation.label,
                href: settings.url_args,
                target: settings.target,
                confirmation_text: operation.confirm,
                func: function (e) {
                    e.preventDefault();
                    var label = $(e.target).html();
                    if (operation.onclick) {
                        operation.onclick(item.encode_id);
                    } else {
                        self.execute(this.findItemByHtml(label));
                    }
                },
            });
        }
    },

    // Add a condition to the grid filter; this adds the condition and refreshes the grid.
    add_filter_condition: function (name, value) {
        // Do nothing is value is empty.
        if (value === "") {
            return false;
        }

        // Add condition to grid.
        this.grid.add_filter(name, value, true);

        // Add button that displays filter and provides a button to delete it.
        var t = $(Templates.filter_element(name, value));
        var self = this;
        t.click(function () {
            // Remove visible element.
            $(this).remove();

            // Remove filter condition.
            self.remove_filter_condition(name, value);
        });

        // append to container
        var container = this.$el.find(`#${name}-filtering-criteria`);
        container.append(t);

        // execute
        this.go_page_one();
        this.execute();
    },

    // Remove a condition to the grid filter; this adds the condition and refreshes the grid.
    remove_filter_condition: function (name, value) {
        // Remove filter condition.
        this.grid.remove_filter(name, value);

        // Execute
        this.go_page_one();
        this.execute();
    },

    // Set sort condition for grid.
    set_sort_condition: function (col_key) {
        // Set new sort condition. New sort is col_key if sorting new column; if reversing sort on
        // currently sorted column, sort is reversed.
        var cur_sort = this.grid.get("sort_key");
        var new_sort = col_key;
        if (cur_sort.indexOf(col_key) !== -1) {
            // Reverse sort.
            if (cur_sort.substring(0, 1) !== "-") {
                new_sort = `-${col_key}`;
            }
        }

        // Remove sort arrows elements.
        this.$el.find(".sort-arrow").remove();

        // Add sort arrow element to new sort column.
        var sort_arrow = new_sort.substring(0, 1) == "-" ? "&uarr;" : "&darr;";
        var t = $(`<span>${sort_arrow}</span>`).addClass("sort-arrow");

        // Add to header
        this.$el.find(`#${col_key}-header`).append(t);

        // Update grid.
        this.grid.set("sort_key", new_sort);
        this.go_page_one();
        this.execute();
    },

    // Set new value for categorical filter.
    set_categorical_filter: function (name, new_value) {
        // Update filter hyperlinks to reflect new filter value.
        var category_filter = this.grid.get("categorical_filters")[name];

        var cur_value = this.grid.get("filters")[name];
        var self = this;
        this.$el.find(`.${name}-filter`).each(function () {
            var text = $.trim($(this).text());
            var filter = category_filter[text];
            var filter_value = filter[name];
            if (filter_value == new_value) {
                // Remove filter link since grid will be using this filter. It is assumed that
                // this element has a single child, a hyperlink/anchor with text.
                $(this).empty();
                $(this).addClass("current-filter");
                $(this).append(text);
            } else if (filter_value == cur_value) {
                // Add hyperlink for this filter since grid will no longer be using this filter. It is assumed that
                // this element has a single child, a hyperlink/anchor.
                $(this).empty();
                var t = $(`<a href="javascript:void(0)" role="button">${text}</a>`);
                t.click(() => {
                    self.set_categorical_filter(name, filter_value);
                });
                $(this).removeClass("current-filter");
                $(this).append(t);
            }
        });

        // Update grid.
        this.grid.add_filter(name, new_value);
        this.go_page_one();
        this.execute();
    },

    // Set page to view.
    set_page: function (new_page) {
        // Update page hyperlink to reflect new page.
        var self = this;
        this.$el.find(".page-link").each(function () {
            var id = $(this).attr("id");

            var // Id has form 'page-link-<page_num>
                page_num = parseInt(id.split("-")[2], 10);

            var cur_page = self.grid.get("cur_page");
            var text;
            if (page_num === new_page) {
                // Remove link to page since grid will be on this page. It is assumed that
                // this element has a single child, a hyperlink/anchor with text.
                text = $(this).children().text();
                $(this).empty();
                $(this).addClass("inactive-link");
                $(this).text(text);
            } else if (page_num === cur_page) {
                // Add hyperlink to this page since grid will no longer be on this page. It is assumed that
                // this element has a single child, a hyperlink/anchor.
                text = $(this).text();
                $(this).empty();
                $(this).removeClass("inactive-link");
                var t = $(`<a href="javascript:void(0)" role="button">${text}</a>`);
                t.click(() => {
                    self.set_page(page_num);
                });
                $(this).append(t);
            }
        });

        if (new_page === "all") {
            this.grid.set("cur_page", new_page);
        } else {
            this.grid.set("cur_page", parseInt(new_page, 10));
        }
        this.execute();
    },

    // confirmation/submission of operation request
    submit_operation: function (operation_button, confirmation_text) {
        // identify operation
        var operation_name = $(operation_button).val();

        // verify any item is selected
        var number_of_checked_ids = this.$el.find('input[name="id"]:checked').length;
        if (number_of_checked_ids < 1) {
            return false;
        }

        // Check to see if there's grid confirmation text for this operation
        var operation = _.findWhere(this.grid.attributes.operations, {
            label: operation_name,
        });
        if (operation && !confirmation_text) {
            confirmation_text = operation.confirm || "";
        }

        // collect ids
        var item_ids = [];
        this.$el.find("input[name=id]:checked").each(function () {
            item_ids.push($(this).val());
        });

        // execute operation
        var options = {
            operation: operation_name,
            id: item_ids,
            confirmation_text: confirmation_text,
        };
        if (operation.target == "top" || operation.target == "center") {
            options = _.extend(options, {
                href: operation.href,
                target: operation.target,
            });
        }
        this.execute(options);
        return true;
    },

    check_all_items: function () {
        var check = this.$(".grid-row-select-checkbox");
        var state = this.$("#check_all").prop("checked");
        _.each(check, (c) => {
            $(c).prop("checked", state);
        });
        this.init_grid_elements();
    },

    // Go back to page one; this is useful when a filter is applied.
    go_page_one: function () {
        // Need to go back to page 1 if not showing all.
        var cur_page = this.grid.get("cur_page");
        if (cur_page !== null && cur_page !== undefined && cur_page !== "all") {
            this.grid.set("cur_page", 1);
        }
    },

    //
    // execute operations and hyperlink requests
    //
    execute: function (options) {
        // get url
        var id = null;
        var href = null;
        var operation = null;
        var confirmation_text = null;
        var target = null;

        // check for options
        if (options) {
            // get options
            href = options.href;
            operation = options.operation;
            id = options.id;
            confirmation_text = options.confirmation_text;
            target = options.target;

            // check if input contains the operation tag
            if (href !== undefined && href.indexOf("operation=") != -1) {
                // Get operation, id in hyperlink's href.
                var href_parts = href.split("?");
                if (href_parts.length > 1) {
                    var href_parms_str = href_parts[1];
                    var href_parms = href_parms_str.split("&");
                    for (var index = 0; index < href_parms.length; index++) {
                        if (href_parms[index].indexOf("operation") != -1) {
                            // Found operation parm; get operation value.
                            operation = href_parms[index].split("=")[1];
                            operation = operation.replace(/\+/g, " ");
                        } else if (href_parms[index].indexOf("id") != -1) {
                            // Found id parm; get id value.
                            id = href_parms[index].split("=")[1];
                        }
                    }
                }
            }
        }

        // check for operation details
        if (operation && id) {
            // show confirmation box
            if (
                confirmation_text &&
                confirmation_text !== "" &&
                confirmation_text != "None" &&
                confirmation_text != "null"
            )
                if (!confirm(confirmation_text)) return false;

            // use small characters for operation?!
            operation = operation.toLowerCase();

            // Update grid.
            this.grid.set({
                operation: operation,
                item_ids: id,
            });

            // Do operation. If operation cannot be performed asynchronously, redirect to location.
            if (target == "top") {
                window.top.location = `${href}?${$.param(this.grid.get_url_data())}`;
            } else if (target == "center") {
                $("#galaxy_main").attr("src", `${href}?${$.param(this.grid.get_url_data())}`);
            } else if (this.grid.can_async_op(operation) || this.dict_format) {
                this.update_grid();
            } else {
                this.go_to(target, href);
            }

            // done
            return false;
        }

        // refresh grid
        if (href) {
            this.go_to(target, href);
            return false;
        }

        // refresh grid
        if (this.grid.get("async") || this.dict_format) {
            this.update_grid();
        } else {
            this.go_to(target, href);
        }

        // done
        return false;
    },

    // go to url
    go_to: function (target, href) {
        // get aysnc status
        var async = this.grid.get("async");
        this.grid.set("async", false);

        // get slide status
        var advanced_search = this.$el.find("#advanced-search").is(":visible");
        this.grid.set("advanced_search", advanced_search);

        // get default url
        if (!href) {
            href = `${this.grid.get("url_base")}?${$.param(this.grid.get_url_data())}`;
        }

        // clear grid of transient request attributes.
        this.grid.set({
            operation: undefined,
            item_ids: undefined,
            async: async,
        });
        switch (target) {
            case "center":
                $("#galaxy_main").attr("src", href);
                break;
            case "top":
                window.top.location = href;
                break;
            default:
                window.location = href;
        }
    },

    // Update grid.
    update_grid: function () {
        // If there's an operation, do POST; otherwise, do GET.
        var method = this.grid.get("operation") ? "POST" : "GET";

        // Show overlay to indicate loading and prevent user actions.
        this.$el.find(".loading-elt-overlay").show();
        var self = this;
        $.ajax({
            type: method,
            url: self.grid.get("url_base"),
            data: self.grid.get_url_data(),
            error: function () {
                alert("Grid refresh failed");
            },
            success: function (response_text) {
                // backup
                var embedded = self.grid.get("embedded");
                var insert = self.grid.get("insert");
                var advanced_search = self.$el.find("#advanced-search").is(":visible");

                // request new configuration
                var json = self.dict_format ? response_text : $.parseJSON(response_text);

                // update
                json.embedded = embedded;
                json.insert = insert;
                json.advanced_search = advanced_search;

                // Initialize new grid config
                self.init_grid(json);

                // Hide loading overlay.
                self.$el.find(".loading-elt-overlay").hide();
            },
            complete: function () {
                // Clear grid of transient request attributes.
                self.grid.set({
                    operation: undefined,
                    item_ids: undefined,
                });
            },
        });
    },
});
