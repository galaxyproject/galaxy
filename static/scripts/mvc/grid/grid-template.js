define("mvc/grid/grid-template", ["exports", "utils/utils"], function(exports, _utils) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _utils2 = _interopRequireDefault(_utils);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    exports.default = {
        // template
        grid: function grid(options) {
            var tmpl = "";
            if (options.embedded) {
                tmpl = this.grid_header(options) + this.grid_table(options);
            } else {
                tmpl = "<div class=\"loading-elt-overlay\"></div><table><tr><td width=\"75%\">" + this.grid_header(options) + "</td><td></td><td></td></tr><tr><td width=\"100%\" id=\"grid-message\" valign=\"top\"></td><td></td><td></td></tr></table>" + this.grid_table(options);
            }

            // add info text
            if (options.info_text) {
                tmpl += "<br><div class=\"toolParamHelp\" style=\"clear: both;\">" + options.info_text + "</div>";
            }

            // return
            return tmpl;
        },

        // template
        grid_table: function grid_table() {
            return "\n            <form method=\"post\" onsubmit=\"return false;\">\n                <table id=\"grid-table\" class=\"grid\">\n                    <thead id=\"grid-table-header\"></thead>\n                    <tbody id=\"grid-table-body\"></tbody>\n                    <tfoot id=\"grid-table-footer\"></tfoot>\n                </table>\n            </form>";
        },

        // template
        grid_header: function grid_header(options) {
            var tmpl = '<div class="grid-header">';
            if (!options.embedded) {
                tmpl += "<h2>" + options.title + "</h2>";
            }
            if (options.global_actions) {
                tmpl += '<ul class="manage-table-actions">';
                var show_popup = options.global_actions.length >= 3;
                if (show_popup) {
                    tmpl += '<li><a class="action-button" id="popup-global-actions" class="menubutton">Actions</a></li>' + '<div popupmenu="popup-global-actions">';
                }
                var _iteratorNormalCompletion = true;
                var _didIteratorError = false;
                var _iteratorError = undefined;

                try {
                    for (var _iterator = options.global_actions[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
                        var action = _step.value;

                        tmpl += "<li><a class=\"action-button use-target\" target=\"" + action.target + "\" href=\"" + action.url_args + "\" onclick=\"return false;\" >" + action.label + "</a></li>";
                    }
                } catch (err) {
                    _didIteratorError = true;
                    _iteratorError = err;
                } finally {
                    try {
                        if (!_iteratorNormalCompletion && _iterator.return) {
                            _iterator.return();
                        }
                    } finally {
                        if (_didIteratorError) {
                            throw _iteratorError;
                        }
                    }
                }

                if (show_popup) {
                    tmpl += "</div>";
                }
                tmpl += "</ul>";
            }
            if (options.insert) {
                tmpl += options.insert;
            }

            // add grid filters
            tmpl += this.grid_filters(options);
            tmpl += "</div>";

            // return template
            return tmpl;
        },

        // template
        header: function header(options) {
            // start
            var tmpl = "<tr>";

            // add checkbox
            if (options.show_item_checkboxes) {
                tmpl += "<th>";
                if (options.items.length > 0) {
                    tmpl += '<input type="checkbox" id="check_all" name=select_all_checkbox value="true">' + '<input type="hidden" name=select_all_checkbox value="true">';
                }
                tmpl += "</th>";
            }

            // create header elements
            var _iteratorNormalCompletion2 = true;
            var _didIteratorError2 = false;
            var _iteratorError2 = undefined;

            try {
                for (var _iterator2 = options.columns[Symbol.iterator](), _step2; !(_iteratorNormalCompletion2 = (_step2 = _iterator2.next()).done); _iteratorNormalCompletion2 = true) {
                    var column = _step2.value;

                    if (column.visible) {
                        tmpl += "<th id=\"" + column.key + "-header\">";
                        if (column.href) {
                            tmpl += "<a href=\"" + column.href + "\" class=\"sort-link\" sort_key=\"" + column.key + "\">" + column.label + "</a>";
                        } else {
                            tmpl += column.label;
                        }
                        tmpl += "<span class=\"sort-arrow\">" + column.extra + "</span></th>";
                    }
                }

                // finalize
            } catch (err) {
                _didIteratorError2 = true;
                _iteratorError2 = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion2 && _iterator2.return) {
                        _iterator2.return();
                    }
                } finally {
                    if (_didIteratorError2) {
                        throw _iteratorError2;
                    }
                }
            }

            tmpl += "</tr>";

            // return template
            return tmpl;
        },

        // template
        body: function body(options) {
            // initialize
            var tmpl = "";
            var num_rows_rendered = 0;
            var items_length = options.items.length;

            // empty grid?
            if (items_length === 0) {
                // No results.
                tmpl += '<tr><td colspan="100"><em>No Items</em></td></tr>';
                num_rows_rendered = 1;
            }

            // create rows
            var _iteratorNormalCompletion3 = true;
            var _didIteratorError3 = false;
            var _iteratorError3 = undefined;

            try {
                for (var _iterator3 = options.items[Symbol.iterator](), _step3; !(_iteratorNormalCompletion3 = (_step3 = _iterator3.next()).done); _iteratorNormalCompletion3 = true) {
                    var item = _step3.value;

                    // Tag current
                    tmpl += "<tr ";
                    if (options.current_item_id == item.id) {
                        tmpl += 'class="current"';
                    }
                    tmpl += ">";

                    // Item selection column
                    if (options.show_item_checkboxes) {
                        tmpl += "<td style=\"width: 1.5em;\"><input type=\"checkbox\" name=\"id\" value=\"" + item.encode_id + "\" id=\"" + item.encode_id + "\" class=\"grid-row-select-checkbox\" /></td>";
                    }

                    // Data columns
                    var _iteratorNormalCompletion4 = true;
                    var _didIteratorError4 = false;
                    var _iteratorError4 = undefined;

                    try {
                        for (var _iterator4 = options.columns[Symbol.iterator](), _step4; !(_iteratorNormalCompletion4 = (_step4 = _iterator4.next()).done); _iteratorNormalCompletion4 = true) {
                            var column = _step4.value;

                            if (column.visible) {
                                // Nowrap
                                var nowrap = "";
                                if (column.nowrap) {
                                    nowrap = 'style="white-space:nowrap;"';
                                }

                                // get column settings
                                var column_settings = item.column_config[column.label];

                                // load attributes
                                var link = column_settings.link;
                                var value = column_settings.value;
                                var target = column_settings.target;

                                // unescape value
                                if (jQuery.type(value) === "string") {
                                    value = value.replace(/\/\//g, "/");
                                }

                                // Attach popup menu?
                                var id = "";
                                var cls = "";
                                if (column.attach_popup) {
                                    id = "grid-" + item.encode_id + "-popup";
                                    cls = "menubutton";
                                    if (link !== "") {
                                        cls += " split";
                                    }
                                    cls += " popup";
                                }

                                // Check for row wrapping
                                tmpl += "<td " + nowrap + ">";

                                // Link
                                if (link) {
                                    if (options.operations.length !== 0) {
                                        tmpl += "<div id=\"" + id + "\" class=\"" + cls + "\" style=\"float: left;\">";
                                    }
                                    tmpl += "<a class=\"menubutton-label use-target\" target=\"" + target + "\" href=\"" + link + "\" onclick=\"return false;\">" + value + "</a>";
                                    if (options.operations.length !== 0) {
                                        tmpl += "</div>";
                                    }
                                } else {
                                    tmpl += "<div id=\"" + id + "\" class=\"" + cls + "\"><label id=\"" + column.label_id_prefix + item.encode_id + "\" for=\"" + item.encode_id + "\">" + (value || "") + "</label></div>";
                                }
                                tmpl += "</td>";
                            }
                        }
                    } catch (err) {
                        _didIteratorError4 = true;
                        _iteratorError4 = err;
                    } finally {
                        try {
                            if (!_iteratorNormalCompletion4 && _iterator4.return) {
                                _iterator4.return();
                            }
                        } finally {
                            if (_didIteratorError4) {
                                throw _iteratorError4;
                            }
                        }
                    }

                    tmpl += "</tr>";
                    num_rows_rendered++;
                }
            } catch (err) {
                _didIteratorError3 = true;
                _iteratorError3 = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion3 && _iterator3.return) {
                        _iterator3.return();
                    }
                } finally {
                    if (_didIteratorError3) {
                        throw _iteratorError3;
                    }
                }
            }

            return tmpl;
        },

        // template
        footer: function footer(options) {
            // create template string
            var tmpl = "";

            // paging
            if (options.use_paging && options.num_pages > 1) {
                // get configuration
                var num_page_links = options.num_page_links;
                var cur_page_num = options.cur_page_num;
                var num_pages = options.num_pages;

                // First pass on min page.
                var page_link_range = num_page_links / 2;
                var min_page = cur_page_num - page_link_range;
                var min_offset = 0;
                if (min_page <= 0) {
                    // Min page is too low.
                    min_page = 1;
                    min_offset = page_link_range - (cur_page_num - min_page);
                }

                // Set max page.
                var max_range = page_link_range + min_offset;
                var max_page = cur_page_num + max_range;
                var max_offset;
                if (max_page <= num_pages) {
                    // Max page is fine.
                    max_offset = 0;
                } else {
                    // Max page is too high.
                    max_page = num_pages;
                    // +1 to account for the +1 in the loop below.
                    max_offset = max_range - (max_page + 1 - cur_page_num);
                }

                // Second and final pass on min page to add any unused
                // offset from max to min.
                if (max_offset !== 0) {
                    min_page -= max_offset;
                    if (min_page < 1) {
                        min_page = 1;
                    }
                }

                // template header
                tmpl += '<tr id="page-links-row">';
                if (options.show_item_checkboxes) {
                    tmpl += "<td></td>";
                }
                tmpl += '<td colspan="100">' + '<span id="page-link-container">' + "Page:";

                if (min_page > 1) {
                    tmpl += '<span class="page-link" id="page-link-1"><a href="javascript:void(0);" page_num="1" onclick="return false;">1</a></span> ...';
                }

                // create page urls
                for (var page_index = min_page; page_index < max_page + 1; page_index++) {
                    if (page_index == options.cur_page_num) {
                        tmpl += "<span class=\"page-link inactive-link\" id=\"page-link-" + page_index + "\">" + page_index + "</span>";
                    } else {
                        tmpl += "<span class=\"page-link\" id=\"page-link-" + page_index + "\"><a href=\"javascript:void(0);\" onclick=\"return false;\" page_num=\"" + page_index + "\">" + page_index + "</a></span>";
                    }
                }

                // show last page
                if (max_page < num_pages) {
                    tmpl += "...<span class=\"page-link\" id=\"page-link-" + num_pages + "\"><a href=\"javascript:void(0);\" onclick=\"return false;\" page_num=\"" + num_pages + "\">" + num_pages + "</a></span>";
                }
                tmpl += "</span>";

                // Show all link
                tmpl += "\n                    <span class=\"page-link\" id=\"show-all-link-span\"> | <a href=\"javascript:void(0);\" onclick=\"return false;\" page_num=\"all\">Show All</a></span>\n                    </td>\n                </tr>";
            }

            // Grid operations for multiple items.
            if (options.show_item_checkboxes) {
                // start template
                tmpl += "\n                <tr>\n                    <input type=\"hidden\" id=\"operation\" name=\"operation\" value=\"\">\n                    <td></td>\n                    <td colspan=\"100\">\n                        For <span class=\"grid-selected-count\"></span> selected items: \n            ";

                // configure buttons for operations
                var _iteratorNormalCompletion5 = true;
                var _didIteratorError5 = false;
                var _iteratorError5 = undefined;

                try {
                    for (var _iterator5 = options.operations[Symbol.iterator](), _step5; !(_iteratorNormalCompletion5 = (_step5 = _iterator5.next()).done); _iteratorNormalCompletion5 = true) {
                        var operation = _step5.value;

                        if (operation.allow_multiple) {
                            tmpl += "<input type=\"button\" value=\"" + operation.label + "\" class=\"operation-button action-button\">&nbsp;";
                        }
                    }

                    // finalize template
                } catch (err) {
                    _didIteratorError5 = true;
                    _iteratorError5 = err;
                } finally {
                    try {
                        if (!_iteratorNormalCompletion5 && _iterator5.return) {
                            _iterator5.return();
                        }
                    } finally {
                        if (_didIteratorError5) {
                            throw _iteratorError5;
                        }
                    }
                }

                tmpl += "</td>" + "</tr>";
            }

            // count global operations
            var found_global = false;
            var _iteratorNormalCompletion6 = true;
            var _didIteratorError6 = false;
            var _iteratorError6 = undefined;

            try {
                for (var _iterator6 = options.operations[Symbol.iterator](), _step6; !(_iteratorNormalCompletion6 = (_step6 = _iterator6.next()).done); _iteratorNormalCompletion6 = true) {
                    var _operation = _step6.value;

                    if (_operation.global_operation) {
                        found_global = true;
                        break;
                    }
                }

                // add global operations
            } catch (err) {
                _didIteratorError6 = true;
                _iteratorError6 = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion6 && _iterator6.return) {
                        _iterator6.return();
                    }
                } finally {
                    if (_didIteratorError6) {
                        throw _iteratorError6;
                    }
                }
            }

            if (found_global) {
                tmpl += "<tr>" + '<td colspan="100">';
                var _iteratorNormalCompletion7 = true;
                var _didIteratorError7 = false;
                var _iteratorError7 = undefined;

                try {
                    for (var _iterator7 = options.operations[Symbol.iterator](), _step7; !(_iteratorNormalCompletion7 = (_step7 = _iterator7.next()).done); _iteratorNormalCompletion7 = true) {
                        var _operation2 = _step7.value;

                        if (_operation2.global_operation) {
                            tmpl += "<a class=\"action-button\" href=\"" + _operation2.global_operation + "\">" + _operation2.label + "</a>";
                        }
                    }
                } catch (err) {
                    _didIteratorError7 = true;
                    _iteratorError7 = err;
                } finally {
                    try {
                        if (!_iteratorNormalCompletion7 && _iterator7.return) {
                            _iterator7.return();
                        }
                    } finally {
                        if (_didIteratorError7) {
                            throw _iteratorError7;
                        }
                    }
                }

                tmpl += "</td>" + "</tr>";
            }

            // add legend
            if (options.legend) {
                tmpl += "<tr><td colspan=\"100\">" + options.legend + "</td></tr>";
            }

            // return
            return tmpl;
        },

        // template
        message: function message(options) {
            var status = options.status;
            if (["success", "ok"].indexOf(status) != -1) {
                status = "done";
            }
            return "<p><div class=\"" + status + "message transient-message\">" + _.escape(options.message) + "</div><div style=\"clear: both\"></div></p>";
        },

        // template
        grid_filters: function grid_filters(options) {
            // get filters
            var default_filter_dict = options.default_filter_dict;
            var filters = options.filters;

            // show advanced search if flag set or if there are filters for advanced search fields
            var advanced_search_display = "none";
            if (options.advanced_search) {
                advanced_search_display = "block";
            }

            // identify columns with advanced filtering
            var show_advanced_search_link = false;
            var _iteratorNormalCompletion8 = true;
            var _didIteratorError8 = false;
            var _iteratorError8 = undefined;

            try {
                for (var _iterator8 = options.columns[Symbol.iterator](), _step8; !(_iteratorNormalCompletion8 = (_step8 = _iterator8.next()).done); _iteratorNormalCompletion8 = true) {
                    var column = _step8.value;

                    if (column.filterable == "advanced") {
                        var column_key = column.key;
                        var f_key = filters[column_key];
                        var d_key = default_filter_dict[column_key];
                        if (f_key && d_key && f_key != d_key) {
                            advanced_search_display = "block";
                        }
                        show_advanced_search_link = true;
                    }
                }

                // hide standard search if advanced is shown
            } catch (err) {
                _didIteratorError8 = true;
                _iteratorError8 = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion8 && _iterator8.return) {
                        _iterator8.return();
                    }
                } finally {
                    if (_didIteratorError8) {
                        throw _iteratorError8;
                    }
                }
            }

            var standard_search_display = "block";
            if (advanced_search_display == "block") {
                standard_search_display = "none";
            }

            //
            // standard search
            //
            var tmpl = "<div id=\"standard-search\" style=\"display: " + standard_search_display + ";\"><table><tr><td style=\"padding: 0;\"><table>";

            // add standard filters
            var _iteratorNormalCompletion9 = true;
            var _didIteratorError9 = false;
            var _iteratorError9 = undefined;

            try {
                for (var _iterator9 = options.columns[Symbol.iterator](), _step9; !(_iteratorNormalCompletion9 = (_step9 = _iterator9.next()).done); _iteratorNormalCompletion9 = true) {
                    var _column = _step9.value;

                    if (_column.filterable == "standard") {
                        tmpl += this.grid_column_filter(options, _column);
                    }
                }

                // finalize standard search
            } catch (err) {
                _didIteratorError9 = true;
                _iteratorError9 = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion9 && _iterator9.return) {
                        _iterator9.return();
                    }
                } finally {
                    if (_didIteratorError9) {
                        throw _iteratorError9;
                    }
                }
            }

            tmpl += "</table>" + "</td>" + "</tr>" + "<tr>" + "<td>";

            // show advanced search link in standard display
            if (show_advanced_search_link) {
                tmpl += '<a href="" class="advanced-search-toggle">Advanced Search</a>';
            }

            // finalize standard search display
            tmpl += "</td>" + "</tr>" + "</table>" + "</div>";

            //
            // advanced search
            //
            tmpl += "<div id=\"advanced-search\" style=\"display: " + advanced_search_display + "; margin-top: 5px; border: 1px solid #ccc;\"><table><tr><td style=\"text-align: left\" colspan=\"100\"><a href=\"\" class=\"advanced-search-toggle\">Close Advanced Search</a></td></tr>";

            // add advanced filters
            var _iteratorNormalCompletion10 = true;
            var _didIteratorError10 = false;
            var _iteratorError10 = undefined;

            try {
                for (var _iterator10 = options.columns[Symbol.iterator](), _step10; !(_iteratorNormalCompletion10 = (_step10 = _iterator10.next()).done); _iteratorNormalCompletion10 = true) {
                    var _column2 = _step10.value;

                    if (_column2.filterable == "advanced") {
                        tmpl += this.grid_column_filter(options, _column2);
                    }
                }

                // finalize advanced search template
            } catch (err) {
                _didIteratorError10 = true;
                _iteratorError10 = err;
            } finally {
                try {
                    if (!_iteratorNormalCompletion10 && _iterator10.return) {
                        _iterator10.return();
                    }
                } finally {
                    if (_didIteratorError10) {
                        throw _iteratorError10;
                    }
                }
            }

            tmpl += "</table>" + "</div>";

            // return template
            return tmpl;
        },

        // template
        grid_column_filter: function grid_column_filter(options, column) {
            // collect parameters
            var filters = options.filters;
            var column_label = column.label;
            var column_key = column.key;
            if (column.filterable == "advanced") {
                column_label = column_label.toLowerCase();
            }

            // start
            var tmpl = "<tr>";

            if (column.filterable == "advanced") {
                tmpl += "<td align=\"left\" style=\"padding-left: 10px\">" + column_label + ":</td>";
            }
            tmpl += '<td style="padding-bottom: 1px;">';
            if (column.is_text) {
                tmpl += "<form class=\"text-filter-form\" column_key=\"" + column_key + "\" action=\"" + options.url + "\" method=\"get\" >";
                // Carry forward filtering criteria with hidden inputs.
                var _iteratorNormalCompletion11 = true;
                var _didIteratorError11 = false;
                var _iteratorError11 = undefined;

                try {
                    for (var _iterator11 = options.columns[Symbol.iterator](), _step11; !(_iteratorNormalCompletion11 = (_step11 = _iterator11.next()).done); _iteratorNormalCompletion11 = true) {
                        var _column3 = _step11.value;

                        var filter_value = filters[_column3.key];
                        if (filter_value) {
                            if (filter_value != "All") {
                                if (_column3.is_text) {
                                    filter_value = JSON.stringify(filter_value);
                                }
                                tmpl += "<input type=\"hidden\" id=\"" + _column3.key + "\" name=\"f-" + _column3.key + "\" value=\"" + filter_value + "\"/>";
                            }
                        }
                    }
                    // Print current filtering criteria and links to delete.
                } catch (err) {
                    _didIteratorError11 = true;
                    _iteratorError11 = err;
                } finally {
                    try {
                        if (!_iteratorNormalCompletion11 && _iterator11.return) {
                            _iterator11.return();
                        }
                    } finally {
                        if (_didIteratorError11) {
                            throw _iteratorError11;
                        }
                    }
                }

                tmpl += "<span id=\"" + column_key + "-filtering-criteria\">";

                // add filters
                var column_filter = filters[column_key];
                if (column_filter) {
                    // identify type
                    var type = jQuery.type(column_filter);

                    // single filter value
                    if (type == "string") {
                        if (column_filter != "All") {
                            // append template
                            tmpl += this.filter_element(column_key, column_filter);
                        }
                    }

                    // multiple filter values
                    if (type == "array") {
                        for (var i in column_filter) {
                            // copy filters and remove entry
                            var params = column_filter;
                            params = params.slice(i);

                            // append template
                            tmpl += this.filter_element(column_key, column_filter[i]);
                        }
                    }
                }

                // close span
                tmpl += "</span>";

                // Set value, size of search input field. Minimum size is 20 characters.
                var value = "";
                var size = 20;
                if (column.filterable == "standard") {
                    value = column.label.toLowerCase();
                    if (value.length < 20) {
                        size = value.length;
                    }
                    // +4 to account for space after placeholder
                    size = size + 4;
                }

                // print input field for column
                tmpl += "\n                <span class=\"search-box\">\n                    <input class=\"search-box-input\" id=\"input-" + column_key + "-filter\" name=\"f-" + column_key + "\" type=\"text\" placeholder=\"" + value + "\" size=\"" + size + "\"/>\n                    <button type=\"submit\" style=\"background: transparent; border: none; padding: 4px; margin: 0px;\">\n                        <i class=\"fa fa-search\"></i>\n                    </button>\n                </span>\n            </form>";
            } else {
                // filter criteria
                tmpl += "<span id=\"" + column_key + "-filtering-criteria\">";

                // add category filters
                var seperator = false;
                for (var cf_label in options.categorical_filters[column_key]) {
                    // get category filter
                    var cf = options.categorical_filters[column_key][cf_label];

                    // each filter will have only a single argument, so get that single argument
                    var cf_key = "";
                    var cf_arg = "";
                    for (var key in cf) {
                        cf_key = key;
                        cf_arg = cf[key];
                    }

                    // add seperator
                    if (seperator) {
                        tmpl += " | ";
                    }
                    seperator = true;

                    // add category
                    var filter = filters[column_key];
                    if (filter && cf[column_key] && filter == cf_arg) {
                        tmpl += "<span class=\"categorical-filter " + column_key + "-filter current-filter\">" + cf_label + "</span>";
                    } else {
                        tmpl += "<span class=\"categorical-filter " + column_key + "-filter\"><a href=\"javascript:void(0);\" filter_key=\"" + cf_key + "\" filter_val=\"" + cf_arg + "\">" + cf_label + "</a></span>";
                    }
                }
                tmpl += "</span>";
            }
            tmpl += "</td>" + "</tr>";

            // return template
            return tmpl;
        },

        // template for filter items
        filter_element: function filter_element(filter_key, filter_value) {
            filter_value = _utils2.default.sanitize(filter_value);
            return "<span class=\"text-filter-val\">" + filter_value + "<a href=\"javascript:void(0);\" filter_key=\"" + filter_key + "\" filter_val=\"" + filter_value + "\"><i class=\"fa fa-times\" style=\"padding-left: 5px; padding-bottom: 6px;\"/></a></span>";
        }
    };
});
//# sourceMappingURL=../../../maps/mvc/grid/grid-template.js.map
