webpackJsonp([0],[
/* 0 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(_, Backbone) {var jQuery = __webpack_require__(3),
	    $ = jQuery,
	    GalaxyApp = __webpack_require__(4).GalaxyApp,
	    AdminPanel = __webpack_require__(11),
	    GridView = __webpack_require__(12),
	    Ui = __webpack_require__(17),
	    Router = __webpack_require__(24),
	    Page = __webpack_require__(26);
	
	window.app = function app(options, bootstrapped) {
	    window.Galaxy = new GalaxyApp(options, bootstrapped);
	    Galaxy.debug('admin app');
	    Galaxy.params = Galaxy.config.params;
	
	    /** Routes */
	    var AdminRouter = Router.extend({
	        routes: {
	            '(/)admin(/)user': 'show_user'
	        },
	
	        authenticate: function (args, name) {
	            return Galaxy.user && Galaxy.user.id && Galaxy.user.get('is_admin');
	        },
	
	        show_user: function () {
	            this.page.display(new GridView({ url_base: Galaxy.root + 'dataset/list', dict_format: true }));
	        }
	    });
	
	    $(function () {
	        _.extend(options.config, { active_view: 'admin' });
	        Galaxy.page = new Page.View(_.extend(options, {
	            Left: AdminPanel,
	            Router: AdminRouter
	        }));
	
	        // start the router - which will call any of the routes above
	        Backbone.history.start({
	            root: Galaxy.root,
	            pushState: true
	        });
	    });
	};
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(1), __webpack_require__(2)))

/***/ },
/* 1 */,
/* 2 */,
/* 3 */,
/* 4 */,
/* 5 */,
/* 6 */,
/* 7 */,
/* 8 */,
/* 9 */,
/* 10 */,
/* 11 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(Backbone, $, _) {var _l = __webpack_require__(7);
	
	var AdminPanel = Backbone.View.extend({
	    initialize: function (page, options) {
	        var self = this;
	        this.page = page;
	        this.root = options.root;
	        this.config = options.config;
	        this.settings = options.settings;
	        this.message = options.message;
	        this.status = options.status;
	        this.model = new Backbone.Model({
	            title: _l('Administration')
	        });
	        this.categories = new Backbone.Collection([{
	            title: 'Server',
	            items: [{
	                title: 'Data types registry',
	                url: 'admin/view_datatypes_registry'
	            }, {
	                title: 'Data tables registry',
	                url: 'admin/view_tool_data_tables'
	            }, {
	                title: 'Display applications',
	                url: 'admin/display_applications'
	            }, {
	                title: 'Manage jobs',
	                url: 'admin/jobs'
	            }]
	        }, {
	            title: 'Tools and Tool Shed',
	            items: [{
	                title: 'Search Tool Shed',
	                url: 'admin_toolshed/browse_tool_sheds',
	                enabled: self.settings.is_tool_shed_installed
	            }, {
	                title: 'Search Tool Shed (Beta)',
	                url: 'admin_toolshed/browse_toolsheds',
	                enabled: self.settings.is_tool_shed_installed && self.config.enable_beta_ts_api_install
	            }, {
	                title: 'Monitor installing repositories',
	                url: 'admin_toolshed/monitor_repository_installation?installing_repository_ids=' + self.settings.installing_repository_ids,
	                enabled: self.settings.installing_repository_ids
	            }, {
	                title: 'Manage installed tools',
	                url: 'admin_toolshed/browse_repositories',
	                enabled: self.settings.is_repo_installed
	            }, {
	                title: 'Reset metadata',
	                url: 'admin_toolshed/reset_metadata_on_selected_installed_repositories',
	                enabled: self.settings.is_repo_installed
	            }, {
	                title: 'Download local tool',
	                url: 'admin/package_tool'
	            }, {
	                title: 'Tool lineage',
	                url: 'admin/tool_versions'
	            }, {
	                title: 'Reload a tool\'s configuration',
	                url: 'admin/reload_tool'
	            }, {
	                title: 'Review tool migration stages',
	                url: 'admin/review_tool_migration_stages'
	            }, {
	                title: 'View Tool Error Logs',
	                url: 'admin/tool_errors'
	            }, {
	                title: 'Manage Display Whitelist',
	                url: 'admin/sanitize_whitelist'
	            }, {
	                title: 'Manage Tool Dependencies',
	                url: 'admin/manage_tool_dependencies'
	            }]
	        }, {
	            title: 'User Management',
	            items: [{
	                title: 'Users',
	                url: 'admin/users'
	            }, {
	                title: 'Groups',
	                url: 'admin/groups'
	            }, {
	                title: 'Roles',
	                url: 'admin/roles'
	            }, {
	                title: 'API keys',
	                url: 'userskeys/all_users'
	            }, {
	                title: 'Impersonate a user',
	                url: 'admin/impersonate',
	                enabled: self.config.allow_user_impersonation
	            }]
	        }, {
	            title: 'Data',
	            items: [{
	                title: 'Quotas',
	                url: 'admin/quotas',
	                enabled: self.config.enable_quotas
	            }, {
	                title: 'Data libraries',
	                url: 'library_admin/browse_libraries'
	            }, {
	                title: 'Roles',
	                url: 'admin/roles'
	            }, {
	                title: 'Local data',
	                url: 'data_manager'
	            }]
	        }, {
	            title: 'Form Definitions',
	            items: [{
	                title: 'Form definitions',
	                url: 'forms/browse_form_definitions'
	            }]
	        }, {
	            title: 'Sample Tracking',
	            items: [{
	                title: 'Sequencers and external services',
	                url: 'external_service/browse_external_services'
	            }, {
	                title: 'Request types',
	                url: 'request_type/browse_request_types'
	            }, {
	                title: 'Sequencing requests',
	                url: 'requests_admin/browse_requests'
	            }, {
	                title: 'Find samples',
	                url: 'requests_common/find_samples?cntrller=requests_admin'
	            }]
	        }]);
	        this.setElement(this._template());
	    },
	
	    render: function () {
	        var self = this;
	        this.$el.empty();
	        this.categories.each(function (category) {
	            var $section = $(self._templateSection(category.attributes));
	            var $entries = $section.find('.ui-side-section-body');
	            _.each(category.get('items'), function (item) {
	                if (item.enabled === undefined || item.enabled) {
	                    $entries.append($('<div/>').addClass('ui-side-section-body-title').append($('<a/>').attr({
	                        href: self.root + item.url,
	                        target: 'galaxy_main' }).text(_l(item.title))));
	                }
	            });
	            self.$el.append($section);
	        });
	        this.page.$('#galaxy_main').prop('src', this.root + 'admin/center?message=' + this.message + '&status=' + this.status);
	    },
	
	    _templateSection: function (options) {
	        return ['<div>', '<div class="ui-side-section-title">' + _l(options.title) + '</div>', '<div class="ui-side-section-body"/>', '</div>'].join('');
	    },
	
	    _template: function () {
	        return '<div class="ui-side-panel"/>';
	    },
	
	    toString: function () {
	        return 'adminPanel';
	    }
	});
	
	module.exports = AdminPanel;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 12 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(jQuery, Backbone, $, _) {// This is necessary so that, when nested arrays are used in ajax/post/get methods, square brackets ('[]') are
	// not appended to the identifier of a nested array.
	jQuery.ajaxSettings.traditional = true;
	
	// dependencies
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13), __webpack_require__(14), __webpack_require__(15), __webpack_require__(16)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils, GridModel, Templates, PopupMenu) {
	
	    // grid view
	    return Backbone.View.extend({
	
	        // model
	        grid: null,
	
	        // Initialize
	        initialize: function (grid_config) {
	            this.dict_format = grid_config.dict_format;
	            var self = this;
	            window.add_tag_to_grid_filter = function (tag_name, tag_value) {
	                // Put tag name and value together.
	                var tag = tag_name + (tag_value !== undefined && tag_value !== "" ? ":" + tag_value : "");
	                var advanced_search = $('#advanced-search').is(":visible");
	                if (!advanced_search) {
	                    $('#standard-search').slideToggle('fast');
	                    $('#advanced-search').slideToggle('fast');
	                }
	                self.add_filter_condition("tags", tag);
	            };
	
	            // set element
	            if (this.dict_format) {
	                this.setElement('<div/>');
	                if (grid_config.url_base && !grid_config.items) {
	                    var url_data = {};
	                    _.each(grid_config.filters, function (v, k) {
	                        url_data['f-' + k] = v;
	                    });
	                    $.ajax({
	                        url: grid_config.url_base + '?' + $.param(url_data),
	                        success: function (response) {
	                            response.embedded = grid_config.embedded;
	                            response.filters = grid_config.filters;
	                            self.init_grid(response);
	                        }
	                    });
	                } else {
	                    this.init_grid(grid_config);
	                }
	            } else {
	                this.setElement('#grid-container');
	                this.init_grid(grid_config);
	            }
	
	            // fix padding
	            if (grid_config.use_panels) {
	                $('#center').css({
	                    padding: '10px',
	                    overflow: 'auto'
	                });
	            }
	        },
	
	        // refresh frames
	        handle_refresh: function (refresh_frames) {
	            if (refresh_frames) {
	                if ($.inArray('history', refresh_frames) > -1) {
	                    if (top.Galaxy && top.Galaxy.currHistoryPanel) {
	                        top.Galaxy.currHistoryPanel.loadCurrentHistory();
	                    }
	                }
	            }
	        },
	
	        // Initialize
	        init_grid: function (grid_config) {
	            // link grid model
	            this.grid = new GridModel(grid_config);
	
	            // get options
	            var options = this.grid.attributes;
	
	            // handle refresh requests
	            this.handle_refresh(options.refresh_frames);
	
	            // strip protocol and domain
	            var url = this.grid.get('url_base');
	            url = url.replace(/^.*\/\/[^\/]+/, '');
	            this.grid.set('url_base', url);
	
	            // append main template
	            this.$el.html(Templates.grid(options));
	
	            // update div contents
	            this.$el.find('#grid-table-header').html(Templates.header(options));
	            this.$el.find('#grid-table-body').html(Templates.body(options));
	            this.$el.find('#grid-table-footer').html(Templates.footer(options));
	
	            // update message
	            if (options.message) {
	                this.$el.find('#grid-message').html(Templates.message(options));
	                var self = this;
	                if (options.use_hide_message) {
	                    setTimeout(function () {
	                        self.$el.find('#grid-message').html('');
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
	            this.$el.find('.operation-button').each(function () {
	                $(this).off();
	                $(this).click(function () {
	                    self.submit_operation(this);
	                    return false;
	                });
	            });
	
	            // Initialize text filters to select text on click and use normal font when user is typing.
	            this.$el.find('input[type=text]').each(function () {
	                $(this).off();
	                $(this).click(function () {
	                    $(this).select();
	                }).keyup(function () {
	                    $(this).css('font-style', 'normal');
	                });
	            });
	
	            // Initialize sort links.
	            this.$el.find('.sort-link').each(function () {
	                $(this).off();
	                $(this).click(function () {
	                    self.set_sort_condition($(this).attr('sort_key'));
	                    return false;
	                });
	            });
	
	            // Initialize text filters.
	            this.$el.find('.text-filter-form').each(function () {
	                $(this).off();
	                $(this).submit(function () {
	                    var column_key = $(this).attr('column_key');
	                    var text_input_obj = $('#input-' + column_key + '-filter');
	                    var text_input = text_input_obj.val();
	                    text_input_obj.val('');
	                    self.add_filter_condition(column_key, text_input);
	                    return false;
	                });
	            });
	
	            // Initialize categorical filters.
	            this.$el.find('.text-filter-val > a').each(function () {
	                $(this).off();
	                $(this).click(function () {
	                    // Remove visible element.
	                    $(this).parent().remove();
	
	                    // Remove filter condition.
	                    self.remove_filter_condition($(this).attr('filter_key'), $(this).attr('filter_val'));
	
	                    // Return
	                    return false;
	                });
	            });
	
	            // Initialize categorical filters.
	            this.$el.find('.categorical-filter > a').each(function () {
	                $(this).off();
	                $(this).click(function () {
	                    self.set_categorical_filter($(this).attr('filter_key'), $(this).attr('filter_val'));
	                    return false;
	                });
	            });
	
	            // Initialize standard, advanced search toggles.
	            this.$el.find('.advanced-search-toggle').each(function () {
	                $(this).off();
	                $(this).click(function () {
	                    self.$el.find('#standard-search').slideToggle('fast');
	                    self.$el.find('#advanced-search').slideToggle('fast');
	                    return false;
	                });
	            });
	
	            // Add event to check all box
	            this.$el.find('#check_all').off();
	            this.$el.find('#check_all').on('click', function () {
	                self.check_all_items();
	            });
	        },
	
	        // Initialize grid elements.
	        init_grid_elements: function () {
	            // Initialize grid selection checkboxes.
	            this.$el.find('.grid').each(function () {
	                var checkboxes = $(this).find("input.grid-row-select-checkbox");
	                var check_count = $(this).find("span.grid-selected-count");
	                var update_checked = function () {
	                    check_count.text($(checkboxes).filter(":checked").length);
	                };
	
	                $(checkboxes).each(function () {
	                    $(this).change(update_checked);
	                });
	                update_checked();
	            });
	
	            // Initialize ratings.
	            if (this.$el.find('.community_rating_star').length !== 0) this.$el.find('.community_rating_star').rating({});
	
	            // get options
	            var options = this.grid.attributes;
	            var self = this;
	
	            //
	            // add page click events
	            //
	            this.$el.find('.page-link > a').each(function () {
	                $(this).click(function () {
	                    self.set_page($(this).attr('page_num'));
	                    return false;
	                });
	            });
	
	            //
	            // add inbound/outbound events
	            //
	            this.$el.find('.use-target').each(function () {
	                $(this).click(function (e) {
	                    self.execute({
	                        href: $(this).attr('href'),
	                        target: $(this).attr('target')
	                    });
	                    return false;
	                });
	            });
	
	            // empty grid?
	            var items_length = options.items.length;
	            if (items_length == 0) {
	                return;
	            }
	
	            // add operation popup menus
	            _.each(options.items, function (item, index) {
	                var button = self.$('#grid-' + index + '-popup').off();
	                var popup = new PopupMenu(button);
	                _.each(options['operations'], function (operation) {
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
	                    }
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
	            var container = this.$el.find('#' + name + '-filtering-criteria');
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
	            var cur_sort = this.grid.get('sort_key');
	            var new_sort = col_key;
	            if (cur_sort.indexOf(col_key) !== -1) {
	                // Reverse sort.
	                if (cur_sort.substring(0, 1) !== '-') {
	                    new_sort = '-' + col_key;
	                }
	            }
	
	            // Remove sort arrows elements.
	            this.$el.find('.sort-arrow').remove();
	
	            // Add sort arrow element to new sort column.
	            var sort_arrow = new_sort.substring(0, 1) == '-' ? '&uarr;' : '&darr;';
	            var t = $('<span>' + sort_arrow + '</span>').addClass('sort-arrow');
	
	            // Add to header
	            this.$el.find('#' + col_key + '-header').append(t);
	
	            // Update grid.
	            this.grid.set('sort_key', new_sort);
	            this.go_page_one();
	            this.execute();
	        },
	
	        // Set new value for categorical filter.
	        set_categorical_filter: function (name, new_value) {
	            // Update filter hyperlinks to reflect new filter value.
	            var category_filter = this.grid.get('categorical_filters')[name],
	                cur_value = this.grid.get('filters')[name];
	            var self = this;
	            this.$el.find('.' + name + '-filter').each(function () {
	                var text = $.trim($(this).text());
	                var filter = category_filter[text];
	                var filter_value = filter[name];
	                if (filter_value == new_value) {
	                    // Remove filter link since grid will be using this filter. It is assumed that
	                    // this element has a single child, a hyperlink/anchor with text.
	                    $(this).empty();
	                    $(this).addClass('current-filter');
	                    $(this).append(text);
	                } else if (filter_value == cur_value) {
	                    // Add hyperlink for this filter since grid will no longer be using this filter. It is assumed that
	                    // this element has a single child, a hyperlink/anchor.
	                    $(this).empty();
	                    var t = $('<a href="#">' + text + '</a>');
	                    t.click(function () {
	                        self.set_categorical_filter(name, filter_value);
	                    });
	                    $(this).removeClass('current-filter');
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
	            this.$el.find('.page-link').each(function () {
	                var id = $(this).attr('id'),
	                    page_num = parseInt(id.split('-')[2], 10),
	                    // Id has form 'page-link-<page_num>
	                cur_page = self.grid.get('cur_page'),
	                    text;
	                if (page_num === new_page) {
	                    // Remove link to page since grid will be on this page. It is assumed that
	                    // this element has a single child, a hyperlink/anchor with text.
	                    text = $(this).children().text();
	                    $(this).empty();
	                    $(this).addClass('inactive-link');
	                    $(this).text(text);
	                } else if (page_num === cur_page) {
	                    // Add hyperlink to this page since grid will no longer be on this page. It is assumed that
	                    // this element has a single child, a hyperlink/anchor.
	                    text = $(this).text();
	                    $(this).empty();
	                    $(this).removeClass('inactive-link');
	                    var t = $('<a href="#">' + text + '</a>');
	                    t.click(function () {
	                        self.set_page(page_num);
	                    });
	                    $(this).append(t);
	                }
	            });
	
	            if (new_page === 'all') {
	                this.grid.set('cur_page', new_page);
	            } else {
	                this.grid.set('cur_page', parseInt(new_page, 10));
	            }
	            this.execute();
	        },
	
	        // confirmation/submission of operation request
	        submit_operation: function (operation_button, confirmation_text) {
	            // identify operation
	            var operation_name = $(operation_button).val();
	
	            // verify in any item is selected
	            var number_of_checked_ids = this.$el.find('input[name="id"]:checked').length;
	            if (!number_of_checked_ids > 0) {
	                return false;
	            }
	
	            // Check to see if there's grid confirmation text for this operation
	            var operation = _.findWhere(this.grid.attributes.operations, { label: operation_name });
	            if (operation && !confirmation_text) {
	                confirmation_text = operation.confirm || '';
	            }
	
	            // collect ids
	            var item_ids = [];
	            this.$el.find('input[name=id]:checked').each(function () {
	                item_ids.push($(this).val());
	            });
	
	            // execute operation
	            this.execute({
	                operation: operation_name,
	                id: item_ids,
	                confirmation_text: confirmation_text
	            });
	
	            // return
	            return true;
	        },
	
	        check_all_items: function () {
	            var check = this.$('.grid-row-select-checkbox');
	            var state = this.$('#check_all').prop('checked');
	            _.each(check, function (c) {
	                $(c).prop('checked', state);
	            });
	            this.init_grid_elements();
	        },
	
	        // Go back to page one; this is useful when a filter is applied.
	        go_page_one: function () {
	            // Need to go back to page 1 if not showing all.
	            var cur_page = this.grid.get('cur_page');
	            if (cur_page !== null && cur_page !== undefined && cur_page !== 'all') {
	                this.grid.set('cur_page', 1);
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
	                if (href !== undefined && href.indexOf('operation=') != -1) {
	                    // Get operation, id in hyperlink's href.
	                    var href_parts = href.split("?");
	                    if (href_parts.length > 1) {
	                        var href_parms_str = href_parts[1];
	                        var href_parms = href_parms_str.split("&");
	                        for (var index = 0; index < href_parms.length; index++) {
	                            if (href_parms[index].indexOf('operation') != -1) {
	                                // Found operation parm; get operation value.
	                                operation = href_parms[index].split('=')[1];
	                                operation = operation.replace(/\+/g, ' ');
	                            } else if (href_parms[index].indexOf('id') != -1) {
	                                // Found id parm; get id value.
	                                id = href_parms[index].split('=')[1];
	                            }
	                        }
	                    }
	                }
	            }
	
	            // check for operation details
	            if (operation && id) {
	                // show confirmation box
	                if (confirmation_text && confirmation_text != '' && confirmation_text != 'None' && confirmation_text != 'null') if (!confirm(confirmation_text)) return false;
	
	                // use small characters for operation?!
	                operation = operation.toLowerCase();
	
	                // Update grid.
	                this.grid.set({
	                    operation: operation,
	                    item_ids: id
	                });
	
	                // Do operation. If operation cannot be performed asynchronously, redirect to location.
	                if (this.grid.can_async_op(operation) || this.dict_format) {
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
	            if (this.grid.get('async') || this.dict_format) {
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
	            var async = this.grid.get('async');
	            this.grid.set('async', false);
	
	            // get slide status
	            advanced_search = this.$el.find('#advanced-search').is(':visible');
	            this.grid.set('advanced_search', advanced_search);
	
	            // get default url
	            if (!href) {
	                href = this.grid.get('url_base') + '?' + $.param(this.grid.get_url_data());
	            }
	
	            // clear grid of transient request attributes.
	            this.grid.set({
	                operation: undefined,
	                item_ids: undefined,
	                async: async
	            });
	            switch (target) {
	                case 'inbound':
	                    // this currently assumes that there is only a single grid shown at a time
	                    var $div = $('.grid-header').closest('.inbound');
	                    if ($div.length !== 0) {
	                        $div.load(href);
	                        return;
	                    }
	                    break;
	                case 'top':
	                    window.top.location = href;
	                    break;
	                default:
	                    window.location = href;
	            }
	        },
	
	        // Update grid.
	        update_grid: function () {
	            // If there's an operation, do POST; otherwise, do GET.
	            var method = this.grid.get('operation') ? 'POST' : 'GET';
	
	            // Show overlay to indicate loading and prevent user actions.
	            this.$el.find('.loading-elt-overlay').show();
	            var self = this;
	            $.ajax({
	                type: method,
	                url: self.grid.get('url_base'),
	                data: self.grid.get_url_data(),
	                error: function (response) {
	                    alert('Grid refresh failed');
	                },
	                success: function (response_text) {
	
	                    // backup
	                    var embedded = self.grid.get('embedded');
	                    var insert = self.grid.get('insert');
	
	                    // request new configuration
	                    var json = self.dict_format ? response_text : $.parseJSON(response_text);
	
	                    // update
	                    json.embedded = embedded;
	                    json.insert = insert;
	
	                    // Initialize new grid config
	                    self.init_grid(json);
	
	                    // Hide loading overlay.
	                    self.$el.find('.loading-elt-overlay').hide();
	                },
	                complete: function () {
	                    // Clear grid of transient request attributes.
	                    self.grid.set({
	                        operation: undefined,
	                        item_ids: undefined
	                    });
	                }
	            });
	        }
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(3), __webpack_require__(2), __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 13 */,
/* 14 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, _, $) {// dependencies
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [], __WEBPACK_AMD_DEFINE_RESULT__ = function () {
	
	    // grid model
	    return Backbone.Model.extend({
	        defaults: {
	            url_base: '',
	            async: false,
	            async_ops: [],
	            categorical_filters: [],
	            filters: {},
	            sort_key: null,
	            show_item_checkboxes: false,
	            advanced_search: false,
	            cur_page: 1,
	            num_pages: 1,
	            operation: undefined,
	            item_ids: undefined
	        },
	
	        /**
	         * Return true if operation can be done asynchronously.
	         */
	        can_async_op: function (op) {
	            return _.indexOf(this.attributes.async_ops, op) !== -1;
	        },
	
	        /**
	         * Add filtering criterion.
	         */
	        add_filter: function (key, value, append) {
	            // Update URL arg with new condition.            
	            if (append) {
	                // Update or append value.
	                var cur_val = this.attributes.filters[key],
	                    new_val;
	                if (cur_val === null || cur_val === undefined) {
	                    new_val = value;
	                } else if (typeof cur_val == 'string') {
	                    if (cur_val == 'All') {
	                        new_val = value;
	                    } else {
	                        // Replace string with array.
	                        var values = [];
	                        values[0] = cur_val;
	                        values[1] = value;
	                        new_val = values;
	                    }
	                } else {
	                    // Current value is an array.
	                    new_val = cur_val;
	                    new_val.push(value);
	                }
	                this.attributes.filters[key] = new_val;
	            } else {
	                // Replace value.
	                this.attributes.filters[key] = value;
	            }
	        },
	
	        /**
	         * Remove filtering criterion.
	         */
	        remove_filter: function (key, condition) {
	            var cur_val = this.attributes.filters[key];
	            if (cur_val === null || cur_val === undefined) {
	                return false;
	            }
	
	            if (typeof cur_val === 'string') {
	                // overwrite/remove condition.
	                this.attributes.filters[key] = '';
	            } else {
	                // filter contains an array of conditions.
	                var condition_index = _.indexOf(cur_val, condition);
	                if (condition_index !== -1) {
	                    cur_val[condition_index] = '';
	                }
	            }
	        },
	
	        /**
	         * Returns URL data for obtaining a new grid.
	         */
	        get_url_data: function () {
	            var url_data = {
	                async: this.attributes.async,
	                sort: this.attributes.sort_key,
	                page: this.attributes.cur_page,
	                show_item_checkboxes: this.attributes.show_item_checkboxes,
	                advanced_search: this.attributes.advanced_search
	            };
	
	            // Add operation, item_ids only if they have values.
	            if (this.attributes.operation) {
	                url_data.operation = this.attributes.operation;
	            }
	            if (this.attributes.item_ids) {
	                url_data.id = this.attributes.item_ids;
	            }
	
	            // Add filter arguments to data, placing "f-" in front of all arguments.
	            var self = this;
	            _.each(_.pairs(self.attributes.filters), function (k) {
	                url_data['f-' + k[0]] = k[1];
	            });
	            return url_data;
	        },
	
	        // Return URL for obtaining a new grid
	        get_url: function (args) {
	            return this.get('url_base') + '?' + $.param(this.get_url_data()) + '&' + $.param(args);
	        }
	
	    });
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(1), __webpack_require__(3)))

/***/ },
/* 15 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(jQuery) {// dependencies
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils) {
	
	    // grid view templates
	    return {
	        // template
	        grid: function (options) {
	            var tmpl = '';
	            if (options.embedded) {
	                tmpl = this.grid_header(options) + this.grid_table(options);
	            } else {
	                tmpl = '<div class="loading-elt-overlay"></div>' + '<table>' + '<tr>' + '<td width="75%">' + this.grid_header(options) + '</td>' + '<td></td>' + '<td></td>' + '</tr>' + '<tr>' + '<td width="100%" id="grid-message" valign="top"></td>' + '<td></td>' + '<td></td>' + '</tr>' + '</table>' + this.grid_table(options);
	            }
	
	            // add info text
	            if (options.info_text) {
	                tmpl += '<br><div class="toolParamHelp" style="clear: both;">' + options.info_text + '</div>';
	            }
	
	            // return
	            return tmpl;
	        },
	
	        // template
	        grid_table: function (options) {
	            return '<form method="post" onsubmit="return false;">' + '<table id="grid-table" class="grid">' + '<thead id="grid-table-header"></thead>' + '<tbody id="grid-table-body"></tbody>' + '<tfoot id="grid-table-footer"></tfoot>' + '</table>' + '</form>';
	        },
	
	        // template
	        grid_header: function (options) {
	            var tmpl = '<div class="grid-header">';
	            if (!options.embedded) {
	                tmpl += '<h2>' + options.title + '</h2>';
	            }
	            if (options.global_actions) {
	                tmpl += '<ul class="manage-table-actions">';
	                var show_popup = options.global_actions.length >= 3;
	                if (show_popup) {
	                    tmpl += '<li><a class="action-button" id="popup-global-actions" class="menubutton">Actions</a></li>' + '<div popupmenu="popup-global-actions">';
	                }
	                for (i in options.global_actions) {
	                    var action = options.global_actions[i];
	                    tmpl += '<li>' + '<a class="action-button use-target" target="' + action.target + '" href="' + action.url_args + '" onclick="return false;" >' + action.label + '</a>' + '</li>';
	                }
	                if (show_popup) {
	                    tmpl += '</div>';
	                }
	                tmpl += '</ul>';
	            }
	            if (options.insert) {
	                tmpl += options.insert;
	            }
	
	            // add grid filters
	            tmpl += this.grid_filters(options);
	            tmpl += '</div>';
	
	            // return template
	            return tmpl;
	        },
	
	        // template
	        header: function (options) {
	
	            // start
	            var tmpl = '<tr>';
	
	            // add checkbox
	            if (options.show_item_checkboxes) {
	                tmpl += '<th>';
	                if (options.items.length > 0) {
	                    tmpl += '<input type="checkbox" id="check_all" name=select_all_checkbox value="true">' + '<input type="hidden" name=select_all_checkbox value="true">';
	                }
	                tmpl += '</th>';
	            }
	
	            // create header elements
	            for (var i in options.columns) {
	                var column = options.columns[i];
	                if (column.visible) {
	                    tmpl += '<th id="' + column.key + '-header">';
	                    if (column.href) {
	                        tmpl += '<a href="' + column.href + '" class="sort-link" sort_key="' + column.key + '">' + column.label + '</a>';
	                    } else {
	                        tmpl += column.label;
	                    }
	                    tmpl += '<span class="sort-arrow">' + column.extra + '</span>' + '</th>';
	                }
	            }
	
	            // finalize
	            tmpl += '</tr>';
	
	            // return template
	            return tmpl;
	        },
	
	        // template
	        body: function (options) {
	            // initialize
	            var tmpl = '';
	            var num_rows_rendered = 0;
	            var items_length = options.items.length;
	
	            // empty grid?
	            if (items_length == 0) {
	                // No results.
	                tmpl += '<tr><td colspan="100"><em>No Items</em></td></tr>';
	                num_rows_rendered = 1;
	            }
	
	            // create rows
	            for (var i in options.items) {
	
	                // encode ids
	                var item = options.items[i];
	                var encoded_id = item.encode_id;
	                var popupmenu_id = 'grid-' + i + '-popup';
	
	                // Tag current
	                tmpl += '<tr ';
	                if (options.current_item_id == item.id) {
	                    tmpl += 'class="current"';
	                }
	                tmpl += '>';
	
	                // Item selection column
	                if (options.show_item_checkboxes) {
	                    tmpl += '<td style="width: 1.5em;">' + '<input type="checkbox" name="id" value="' + encoded_id + '" id="' + encoded_id + '" class="grid-row-select-checkbox" />' + '</td>';
	                }
	
	                // Data columns
	                for (j in options.columns) {
	                    var column = options.columns[j];
	                    if (column.visible) {
	                        // Nowrap
	                        var nowrap = '';
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
	                        if (jQuery.type(value) === 'string') {
	                            value = value.replace(/\/\//g, '/');
	                        }
	
	                        // Attach popup menu?
	                        var id = '';
	                        var cls = '';
	                        if (column.attach_popup) {
	                            id = 'grid-' + i + '-popup';
	                            cls = 'menubutton';
	                            if (link != '') {
	                                cls += ' split';
	                            }
	                            cls += ' popup';
	                        }
	
	                        // Check for row wrapping
	                        tmpl += '<td ' + nowrap + '>';
	
	                        // Link
	                        if (link) {
	                            if (options.operations.length != 0) {
	                                tmpl += '<div id="' + id + '" class="' + cls + '" style="float: left;">';
	                            }
	                            tmpl += '<a class="menubutton-label use-target" target="' + target + '" href="' + link + '" onclick="return false;">' + value + '</a>';
	                            if (options.operations.length != 0) {
	                                tmpl += '</div>';
	                            }
	                        } else {
	                            tmpl += '<div id="' + id + '" class="' + cls + '"><label id="' + column.label_id_prefix + encoded_id + '" for="' + encoded_id + '">' + (value || '') + '</label></div>';
	                        }
	                        tmpl += '</td>';
	                    }
	                }
	                tmpl += '</tr>';
	                num_rows_rendered++;
	            }
	            return tmpl;
	        },
	
	        // template
	        footer: function (options) {
	
	            // create template string
	            var tmpl = '';
	
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
	                if (max_offset != 0) {
	                    min_page -= max_offset;
	                    if (min_page < 1) {
	                        min_page = 1;
	                    }
	                }
	
	                // template header
	                tmpl += '<tr id="page-links-row">';
	                if (options.show_item_checkboxes) {
	                    tmpl += '<td></td>';
	                }
	                tmpl += '<td colspan="100">' + '<span id="page-link-container">' + 'Page:';
	
	                if (min_page > 1) {
	                    tmpl += '<span class="page-link" id="page-link-1"><a href="javascript:void(0);" page_num="1" onclick="return false;">1</a></span> ...';
	                }
	
	                // create page urls
	                for (var page_index = min_page; page_index < max_page + 1; page_index++) {
	
	                    if (page_index == options.cur_page_num) {
	                        tmpl += '<span class="page-link inactive-link" id="page-link-' + page_index + '">' + page_index + '</span>';
	                    } else {
	                        tmpl += '<span class="page-link" id="page-link-' + page_index + '"><a href="javascript:void(0);" onclick="return false;" page_num="' + page_index + '">' + page_index + '</a></span>';
	                    }
	                }
	
	                // show last page
	                if (max_page < num_pages) {
	                    tmpl += '...' + '<span class="page-link" id="page-link-' + num_pages + '"><a href="javascript:void(0);" onclick="return false;" page_num="' + num_pages + '">' + num_pages + '</a></span>';
	                }
	                tmpl += '</span>';
	
	                // Show all link
	                tmpl += '<span class="page-link" id="show-all-link-span"> | <a href="javascript:void(0);" onclick="return false;" page_num="all">Show All</a></span>' + '</td>' + '</tr>';
	            }
	
	            // Grid operations for multiple items.
	            if (options.show_item_checkboxes) {
	                // start template
	                tmpl += '<tr>' + '<input type="hidden" id="operation" name="operation" value="">' + '<td></td>' + '<td colspan="100">' + 'For <span class="grid-selected-count"></span> selected items: ';
	
	                // configure buttons for operations
	                for (i in options.operations) {
	                    var operation = options.operations[i];
	                    if (operation.allow_multiple) {
	                        tmpl += '<input type="button" value="' + operation.label + '" class="operation-button action-button">&nbsp;';
	                    }
	                }
	
	                // finalize template
	                tmpl += '</td>' + '</tr>';
	            }
	
	            // count global operations
	            var found_global = false;
	            for (i in options.operations) {
	                if (options.operations[i].global_operation) {
	                    found_global = true;
	                    break;
	                }
	            }
	
	            // add global operations
	            if (found_global) {
	                tmpl += '<tr>' + '<td colspan="100">';
	                for (i in options.operations) {
	                    var operation = options.operations[i];
	                    if (operation.global_operation) {
	                        tmpl += '<a class="action-button" href="' + operation.global_operation + '">' + operation.label + '</a>';
	                    }
	                }
	                tmpl += '</td>' + '</tr>';
	            }
	
	            // add legend
	            if (options.legend) {
	                tmpl += '<tr>' + '<td colspan="100">' + options.legend + '</td>' + '</tr>';
	            }
	
	            // return
	            return tmpl;
	        },
	
	        // template
	        message: function (options) {
	            return '<p>' + '<div class="' + options.status + 'message transient-message">' + options.message + '</div>' + '<div style="clear: both"></div>' + '</p>';
	        },
	
	        // template
	        grid_filters: function (options) {
	
	            // get filters
	            var default_filter_dict = options.default_filter_dict;
	            var filters = options.filters;
	
	            // show advanced search if flag set or if there are filters for advanced search fields
	            var advanced_search_display = 'none';
	            if (options.advanced_search) {
	                advanced_search_display = 'block';
	            }
	
	            // identify columns with advanced filtering
	            var show_advanced_search_link = false;
	            for (var i in options.columns) {
	                var column = options.columns[i];
	                if (column.filterable == 'advanced') {
	                    var column_key = column.key;
	                    var f_key = filters[column_key];
	                    var d_key = default_filter_dict[column_key];
	                    if (f_key && d_key && f_key != d_key) {
	                        advanced_search_display = 'block';
	                    }
	                    show_advanced_search_link = true;
	                }
	            }
	
	            // hide standard search if advanced is shown
	            var standard_search_display = 'block';
	            if (advanced_search_display == 'block') {
	                standard_search_display = 'none';
	            }
	
	            //
	            // standard search
	            //
	            var tmpl = '<div id="standard-search" style="display: ' + standard_search_display + ';">' + '<table>' + '<tr>' + '<td style="padding: 0;">' + '<table>';
	
	            // add standard filters
	            for (var i in options.columns) {
	                var column = options.columns[i];
	                if (column.filterable == 'standard') {
	                    tmpl += this.grid_column_filter(options, column);
	                }
	            }
	
	            // finalize standard search
	            tmpl += '</table>' + '</td>' + '</tr>' + '<tr>' + '<td>';
	
	            // show advanced search link in standard display
	            if (show_advanced_search_link) {
	                tmpl += '<a href="" class="advanced-search-toggle">Advanced Search</a>';
	            }
	
	            // finalize standard search display
	            tmpl += '</td>' + '</tr>' + '</table>' + '</div>';
	
	            //
	            // advanced search
	            //
	            tmpl += '<div id="advanced-search" style="display: ' + advanced_search_display + '; margin-top: 5px; border: 1px solid #ccc;">' + '<table>' + '<tr>' + '<td style="text-align: left" colspan="100">' + '<a href="" class="advanced-search-toggle">Close Advanced Search</a>' + '</td>' + '</tr>';
	
	            // add advanced filters
	            for (var i in options.columns) {
	                var column = options.columns[i];
	                if (column.filterable == 'advanced') {
	                    tmpl += this.grid_column_filter(options, column);
	                }
	            }
	
	            // finalize advanced search template
	            tmpl += '</table>' + '</div>';
	
	            // return template
	            return tmpl;
	        },
	
	        // template
	        grid_column_filter: function (options, column) {
	
	            // collect parameters
	            var default_filter_dict = options.default_filter_dict;
	            var filters = options.filters;
	            var column_label = column.label;
	            var column_key = column.key;
	            if (column.filterable == 'advanced') {
	                column_label = column_label.toLowerCase();
	            }
	
	            // start
	            var tmpl = '<tr>';
	
	            if (column.filterable == 'advanced') {
	                tmpl += '<td align="left" style="padding-left: 10px">' + column_label + ':</td>';
	            }
	            tmpl += '<td style="padding-bottom: 1px;">';
	            if (column.is_text) {
	                tmpl += '<form class="text-filter-form" column_key="' + column_key + '" action="' + options.url + '" method="get" >';
	                // Carry forward filtering criteria with hidden inputs.
	                for (i in options.columns) {
	                    var temp_column = options.columns[i];
	                    var filter_value = filters[temp_column.key];
	                    if (filter_value) {
	                        if (filter_value != 'All') {
	                            if (temp_column.is_text) {
	                                filter_value = JSON.stringify(filter_value);
	                            }
	                            tmpl += '<input type="hidden" id="' + temp_column.key + '" name="f-' + temp_column.key + '" value="' + filter_value + '"/>';
	                        }
	                    }
	                }
	                // Print current filtering criteria and links to delete.
	                tmpl += '<span id="' + column_key + '-filtering-criteria">';
	
	                // add filters
	                var column_filter = filters[column_key];
	                if (column_filter) {
	                    // identify type
	                    var type = jQuery.type(column_filter);
	
	                    // single filter value
	                    if (type == 'string') {
	                        if (column_filter != 'All') {
	                            // append template
	                            tmpl += this.filter_element(column_key, column_filter);
	                        }
	                    }
	
	                    // multiple filter values
	                    if (type == 'array') {
	                        for (var i in column_filter) {
	                            // get filter
	                            var filter = column_filter[i];
	
	                            // copy filters and remove entry
	                            var params = column_filter;
	                            params = params.slice(i);
	
	                            // append template
	                            tmpl += this.filter_element(column_key, filter);
	                        }
	                    }
	                }
	
	                // close span
	                tmpl += '</span>';
	
	                // Set value, size of search input field. Minimum size is 20 characters.
	                var value = '';
	                if (column.filterable == 'standard') {
	                    value = column.label.toLowerCase();
	                    var size = value.length;
	                    if (size < 20) {
	                        size = 20;
	                    }
	                    // +4 to account for space after placeholder
	                    size = size + 4;
	                }
	
	                // print input field for column
	                tmpl += '<span class="search-box">' + '<input class="search-box-input" id="input-' + column_key + '-filter" name="f-' + column_key + '" type="text" placeholder="' + value + '" size="' + size + '"/>' + '<button type="submit" style="background: transparent; border: none; padding: 4px; margin: 0px;">' + '<i class="fa fa-search"></i>' + '</button>' + '</span>' + '</form>';
	            } else {
	                // filter criteria
	                tmpl += '<span id="' + column_key + '-filtering-criteria">';
	
	                // add category filters
	                var seperator = false;
	                for (cf_label in options.categorical_filters[column_key]) {
	                    // get category filter
	                    var cf = options.categorical_filters[column_key][cf_label];
	
	                    // each filter will have only a single argument, so get that single argument
	                    var cf_key = '';
	                    var cf_arg = '';
	                    for (key in cf) {
	                        cf_key = key;
	                        cf_arg = cf[key];
	                    }
	
	                    // add seperator
	                    if (seperator) {
	                        tmpl += ' | ';
	                    }
	                    seperator = true;
	
	                    // add category
	                    var filter = filters[column_key];
	                    if (filter && cf[column_key] && filter == cf_arg) {
	                        tmpl += '<span class="categorical-filter ' + column_key + '-filter current-filter">' + cf_label + '</span>';
	                    } else {
	                        tmpl += '<span class="categorical-filter ' + column_key + '-filter">' + '<a href="javascript:void(0);" filter_key="' + cf_key + '" filter_val="' + cf_arg + '">' + cf_label + '</a>' + '</span>';
	                    }
	                }
	                tmpl += '</span>';
	            }
	            tmpl += '</td>' + '</tr>';
	
	            // return template
	            return tmpl;
	        },
	
	        // template for filter items
	        filter_element: function (filter_key, filter_value) {
	            filter_value = Utils.sanitize(filter_value);
	            return '<span class="text-filter-val">' + filter_value + '<a href="javascript:void(0);" filter_key="' + filter_key + '" filter_val="' + filter_value + '">' + '<i class="fa fa-times" style="padding-left: 5px; padding-bottom: 6px;"/>' + '</a>' + '</span>';
	        }
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(3)))

/***/ },
/* 16 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $, _, jQuery) {!(__WEBPACK_AMD_DEFINE_ARRAY__ = [
	    //jquery
	    //backbone
	], __WEBPACK_AMD_DEFINE_RESULT__ = function () {
	    // =============================================================================
	    /**
	     * view for a popup menu
	     */
	    var PopupMenu = Backbone.View.extend({
	        //TODO: maybe better as singleton off the Galaxy obj
	        /** Cache the desired button element and options, set up the button click handler
	         *  NOTE: attaches this view as HTML/jQ data on the button for later use.
	         */
	        initialize: function ($button, options) {
	            // default settings
	            this.$button = $button;
	            if (!this.$button.length) {
	                this.$button = $('<div/>');
	            }
	            this.options = options || [];
	            this.$button.data('popupmenu', this);
	
	            // set up button click -> open menu behavior
	            var menu = this;
	            this.$button.click(function (event) {
	                // if there's already a menu open, remove it
	                $('.popmenu-wrapper').remove();
	                menu._renderAndShow(event);
	                return false;
	            });
	        },
	
	        // render the menu, append to the page body at the click position, and set up the 'click-away' handlers, show
	        _renderAndShow: function (clickEvent) {
	            this.render();
	            this.$el.appendTo('body').css(this._getShownPosition(clickEvent)).show();
	            this._setUpCloseBehavior();
	        },
	
	        // render the menu
	        // this menu doesn't attach itself to the DOM ( see _renderAndShow )
	        render: function () {
	            // render the menu body absolute and hidden, fill with template
	            this.$el.addClass('popmenu-wrapper').hide().css({ position: 'absolute' }).html(this.template(this.$button.attr('id'), this.options));
	
	            // set up behavior on each link/anchor elem
	            if (this.options.length) {
	                var menu = this;
	                //precondition: there should be one option per li
	                this.$el.find('li').each(function (i, li) {
	                    var option = menu.options[i];
	
	                    // if the option has 'func', call that function when the anchor is clicked
	                    if (option.func) {
	                        $(this).children('a.popupmenu-option').click(function (event) {
	                            option.func.call(menu, event, option);
	                            // We must preventDefault otherwise clicking "cancel"
	                            // on a purge or something still navigates and causes
	                            // the action.
	                            event.preventDefault();
	                            // bubble up so that an option click will call the close behavior
	                        });
	                    }
	                });
	            }
	            return this;
	        },
	
	        template: function (id, options) {
	            return ['<ul id="', id, '-menu" class="dropdown-menu">', this._templateOptions(options), '</ul>'].join('');
	        },
	
	        _templateOptions: function (options) {
	            if (!options.length) {
	                return '<li>(no options)</li>';
	            }
	            return _.map(options, function (option) {
	                if (option.divider) {
	                    return '<li class="divider"></li>';
	                } else if (option.header) {
	                    return ['<li class="head"><a href="javascript:void(0);">', option.html, '</a></li>'].join('');
	                }
	                var href = option.href || 'javascript:void(0);',
	                    target = option.target ? ' target="' + option.target + '"' : '',
	                    check = option.checked ? '<span class="fa fa-check"></span>' : '';
	                return ['<li><a class="popupmenu-option" href="', href, '"', target, '>', check, option.html, '</a></li>'].join('');
	            }).join('');
	        },
	
	        // get the absolute position/offset for the menu
	        _getShownPosition: function (clickEvent) {
	
	            // display menu horiz. centered on click...
	            var menuWidth = this.$el.width();
	            var x = clickEvent.pageX - menuWidth / 2;
	
	            // adjust to handle horiz. scroll and window dimensions ( draw entirely on visible screen area )
	            x = Math.min(x, $(document).scrollLeft() + $(window).width() - menuWidth - 5);
	            x = Math.max(x, $(document).scrollLeft() + 5);
	            return {
	                top: clickEvent.pageY,
	                left: x
	            };
	        },
	
	        // bind an event handler to all available frames so that when anything is clicked
	        // the menu is removed from the DOM and the event handler unbinds itself
	        _setUpCloseBehavior: function () {
	            var menu = this;
	            //TODO: alternately: focus hack, blocking overlay, jquery.blockui
	
	            // function to close popup and unbind itself
	            function closePopup(event) {
	                $(document).off('click.close_popup');
	                if (window && window.parent !== window) {
	                    try {
	                        $(window.parent.document).off("click.close_popup");
	                    } catch (err) {}
	                } else {
	                    try {
	                        $('iframe#galaxy_main').contents().off("click.close_popup");
	                    } catch (err) {}
	                }
	                menu.remove();
	            }
	
	            $('html').one("click.close_popup", closePopup);
	            if (window && window.parent !== window) {
	                try {
	                    $(window.parent.document).find('html').one("click.close_popup", closePopup);
	                } catch (err) {}
	            } else {
	                try {
	                    $('iframe#galaxy_main').contents().one("click.close_popup", closePopup);
	                } catch (err) {}
	            }
	        },
	
	        // add a menu option/item at the given index
	        addItem: function (item, index) {
	            // append to end if no index
	            index = index >= 0 ? index : this.options.length;
	            this.options.splice(index, 0, item);
	            return this;
	        },
	
	        // remove a menu option/item at the given index
	        removeItem: function (index) {
	            if (index >= 0) {
	                this.options.splice(index, 1);
	            }
	            return this;
	        },
	
	        // search for a menu option by its html
	        findIndexByHtml: function (html) {
	            for (var i = 0; i < this.options.length; i++) {
	                if (_.has(this.options[i], 'html') && this.options[i].html === html) {
	                    return i;
	                }
	            }
	            return null;
	        },
	
	        // search for a menu option by its html
	        findItemByHtml: function (html) {
	            return this.options[this.findIndexByHtml(html)];
	        },
	
	        // string representation
	        toString: function () {
	            return 'PopupMenu';
	        }
	    });
	    /** shortcut to new for when you don't need to preserve the ref */
	    PopupMenu.create = function _create($button, options) {
	        return new PopupMenu($button, options);
	    };
	
	    // -----------------------------------------------------------------------------
	    // the following class functions are bridges from the original make_popupmenu and make_popup_menus
	    // to the newer backbone.js PopupMenu
	
	    /** Create a PopupMenu from simple map initial_options activated by clicking button_element.
	     *      Converts initial_options to object array used by PopupMenu.
	     *  @param {jQuery|DOMElement} button_element element which, when clicked, activates menu
	     *  @param {Object} initial_options map of key -> values, where
	     *      key is option text, value is fn to call when option is clicked
	     *  @returns {PopupMenu} the PopupMenu created
	     */
	    PopupMenu.make_popupmenu = function (button_element, initial_options) {
	        var convertedOptions = [];
	        _.each(initial_options, function (optionVal, optionKey) {
	            var newOption = { html: optionKey };
	
	            // keys with null values indicate: header
	            if (optionVal === null) {
	                // !optionVal? (null only?)
	                newOption.header = true;
	
	                // keys with function values indicate: a menu option
	            } else if (jQuery.type(optionVal) === 'function') {
	                newOption.func = optionVal;
	            }
	            //TODO:?? any other special optionVals?
	            // there was no divider option originally
	            convertedOptions.push(newOption);
	        });
	        return new PopupMenu($(button_element), convertedOptions);
	    };
	
	    /** Find all anchors in $parent (using selector) and covert anchors into a PopupMenu options map.
	     *  @param {jQuery} $parent the element that contains the links to convert to options
	     *  @param {String} selector jq selector string to find links
	     *  @returns {Object[]} the options array to initialize a PopupMenu
	     */
	    //TODO: lose parent and selector, pass in array of links, use map to return options
	    PopupMenu.convertLinksToOptions = function ($parent, selector) {
	        $parent = $($parent);
	        selector = selector || 'a';
	        var options = [];
	        $parent.find(selector).each(function (elem, i) {
	            var option = {},
	                $link = $(elem);
	
	            // convert link text to the option text (html) and the href into the option func
	            option.html = $link.text();
	            if ($link.attr('href')) {
	                var linkHref = $link.attr('href'),
	                    linkTarget = $link.attr('target'),
	                    confirmText = $link.attr('confirm');
	
	                option.func = function () {
	                    // if there's a "confirm" attribute, throw up a confirmation dialog, and
	                    //  if the user cancels - do nothing
	                    if (confirmText && !confirm(confirmText)) {
	                        return;
	                    }
	
	                    // if there's no confirm attribute, or the user accepted the confirm dialog:
	                    switch (linkTarget) {
	                        // relocate the center panel
	                        case '_parent':
	                            window.parent.location = linkHref;
	                            break;
	
	                        // relocate the entire window
	                        case '_top':
	                            window.top.location = linkHref;
	                            break;
	
	                        // relocate this panel
	                        default:
	                            window.location = linkHref;
	                    }
	                };
	            }
	            options.push(option);
	        });
	        return options;
	    };
	
	    /** Create a single popupmenu from existing DOM button and anchor elements
	     *  @param {jQuery} $buttonElement the element that when clicked will open the menu
	     *  @param {jQuery} $menuElement the element that contains the anchors to convert into a menu
	     *  @param {String} menuElementLinkSelector jq selector string used to find anchors to be made into menu options
	     *  @returns {PopupMenu} the PopupMenu (Backbone View) that can render, control the menu
	     */
	    PopupMenu.fromExistingDom = function ($buttonElement, $menuElement, menuElementLinkSelector) {
	        $buttonElement = $($buttonElement);
	        $menuElement = $($menuElement);
	        var options = PopupMenu.convertLinksToOptions($menuElement, menuElementLinkSelector);
	        // we're done with the menu (having converted it to an options map)
	        $menuElement.remove();
	        return new PopupMenu($buttonElement, options);
	    };
	
	    /** Create all popupmenus within a document or a more specific element
	     *  @param {DOMElement} parent the DOM element in which to search for popupmenus to build (defaults to document)
	     *  @param {String} menuSelector jq selector string to find popupmenu menu elements (defaults to "div[popupmenu]")
	     *  @param {Function} buttonSelectorBuildFn the function to build the jq button selector.
	     *      Will be passed $menuElement, parent.
	     *      (Defaults to return '#' + $menuElement.attr( 'popupmenu' ); )
	     *  @returns {PopupMenu[]} array of popupmenus created
	     */
	    PopupMenu.make_popup_menus = function (parent, menuSelector, buttonSelectorBuildFn) {
	        parent = parent || document;
	        // orig. Glx popupmenu menus have a (non-std) attribute 'popupmenu'
	        //  which contains the id of the button that activates the menu
	        menuSelector = menuSelector || 'div[popupmenu]';
	        // default to (orig. Glx) matching button to menu by using the popupmenu attr of the menu as the id of the button
	        buttonSelectorBuildFn = buttonSelectorBuildFn || function ($menuElement, parent) {
	            return '#' + $menuElement.attr('popupmenu');
	        };
	
	        // aggregate and return all PopupMenus
	        var popupMenusCreated = [];
	        $(parent).find(menuSelector).each(function () {
	            var $menuElement = $(this),
	                $buttonElement = $(parent).find(buttonSelectorBuildFn($menuElement, parent));
	            popupMenusCreated.push(PopupMenu.fromDom($buttonElement, $menuElement));
	            $buttonElement.addClass('popup');
	        });
	        return popupMenusCreated;
	    };
	
	    // =============================================================================
	    return PopupMenu;
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(3), __webpack_require__(1), __webpack_require__(3)))

/***/ },
/* 17 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $, _) {/**
	 *  This class contains backbone wrappers for basic ui elements such as Images, Labels, Buttons, Input fields etc.
	 */
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13), __webpack_require__(18), __webpack_require__(20), __webpack_require__(21), __webpack_require__(22), __webpack_require__(19), __webpack_require__(23)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils, Select, Slider, Options, Drilldown, Buttons, Modal) {
	
	    /** Label wrapper */
	    var Label = Backbone.View.extend({
	        tagName: 'label',
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model(options);
	            this.tagName = options.tagName || this.tagName;
	            this.setElement($('<' + this.tagName + '/>'));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	        title: function (new_title) {
	            this.model.set('title', new_title);
	        },
	        value: function () {
	            return this.model.get('title');
	        },
	        render: function () {
	            this.$el.removeClass().addClass('ui-label').addClass(this.model.get('cls')).html(this.model.get('title'));
	            return this;
	        }
	    });
	
	    /** Displays messages used e.g. in the tool form */
	    var Message = Backbone.View.extend({
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model({
	                message: null,
	                status: 'info',
	                cls: '',
	                persistent: false,
	                fade: true
	            }).set(options);
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	        update: function (options) {
	            this.model.set(options);
	        },
	        render: function () {
	            this.$el.removeClass().addClass('ui-message').addClass(this.model.get('cls'));
	            var status = this.model.get('status');
	            if (this.model.get('large')) {
	                this.$el.addClass((status == 'success' && 'done' || status == 'danger' && 'error' || status) + 'messagelarge');
	            } else {
	                this.$el.addClass('alert').addClass('alert-' + status);
	            }
	            if (this.model.get('message')) {
	                this.$el.html(this.messageForDisplay());
	                this.$el[this.model.get('fade') ? 'fadeIn' : 'show']();
	                this.timeout && window.clearTimeout(this.timeout);
	                if (!this.model.get('persistent')) {
	                    var self = this;
	                    this.timeout = window.setTimeout(function () {
	                        self.model.set('message', '');
	                    }, 3000);
	                }
	            } else {
	                this.$el.fadeOut();
	            }
	            return this;
	        },
	        messageForDisplay: function () {
	            return _.escape(this.model.get('message'));
	        }
	    });
	
	    var UnescapedMessage = Message.extend({
	        messageForDisplay: function () {
	            return this.model.get('message');
	        }
	    });
	
	    /** Renders an input element used e.g. in the tool form */
	    var Input = Backbone.View.extend({
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model({
	                type: 'text',
	                placeholder: '',
	                disabled: false,
	                readonly: false,
	                visible: true,
	                cls: '',
	                area: false,
	                color: null,
	                style: null
	            }).set(options);
	            this.tagName = this.model.get('area') ? 'textarea' : 'input';
	            this.setElement($('<' + this.tagName + '/>'));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	        events: {
	            'input': '_onchange'
	        },
	        value: function (new_val) {
	            new_val !== undefined && this.model.set('value', typeof new_val === 'string' ? new_val : '');
	            return this.model.get('value');
	        },
	        render: function () {
	            var self = this;
	            this.$el.removeClass().addClass('ui-' + this.tagName).addClass(this.model.get('cls')).addClass(this.model.get('style')).attr('id', this.model.id).attr('type', this.model.get('type')).attr('placeholder', this.model.get('placeholder')).css('color', this.model.get('color') || '').css('border-color', this.model.get('color') || '');
	            var datalist = this.model.get('datalist');
	            if ($.isArray(datalist) && datalist.length > 0) {
	                this.$el.autocomplete({ source: function (request, response) {
	                        response(self.model.get('datalist'));
	                    },
	                    change: function () {
	                        self._onchange();
	                    } });
	            }
	            if (this.model.get('value') !== this.$el.val()) {
	                this.$el.val(this.model.get('value'));
	            }
	            _.each(['readonly', 'disabled'], function (attr_name) {
	                self.model.get(attr_name) ? self.$el.attr(attr_name, true) : self.$el.removeAttr(attr_name);
	            });
	            this.$el[this.model.get('visible') ? 'show' : 'hide']();
	            return this;
	        },
	        _onchange: function () {
	            this.value(this.$el.val());
	            this.model.get('onchange') && this.model.get('onchange')(this.model.get('value'));
	        }
	    });
	
	    /** Creates a hidden element input field used e.g. in the tool form */
	    var Hidden = Backbone.View.extend({
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model(options);
	            this.setElement($('<div/>').append(this.$info = $('<div/>')).append(this.$hidden = $('<div/>')));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	        value: function (new_val) {
	            new_val !== undefined && this.model.set('value', new_val);
	            return this.model.get('value');
	        },
	        render: function () {
	            this.$el.attr('id', this.model.id);
	            this.$hidden.val(this.model.get('value'));
	            this.model.get('info') ? this.$info.show().text(this.model.get('info')) : this.$info.hide();
	            return this;
	        }
	    });
	
	    /** Creates a upload element input field */
	    var Upload = Backbone.View.extend({
	        initialize: function (options) {
	            var self = this;
	            this.model = options && options.model || new Backbone.Model(options);
	            this.setElement($('<div/>').append(this.$info = $('<div/>')).append(this.$file = $('<input/>').attr('type', 'file').addClass('ui-margin-bottom')).append(this.$text = $('<textarea/>').addClass('ui-textarea').attr('disabled', true)).append(this.$wait = $('<i/>').addClass('fa fa-spinner fa-spin')));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.$file.on('change', function (e) {
	                self._readFile(e);
	            });
	            this.render();
	        },
	        value: function (new_val) {
	            new_val !== undefined && this.model.set('value', new_val);
	            return this.model.get('value');
	        },
	        render: function () {
	            this.$el.attr('id', this.model.id);
	            this.model.get('info') ? this.$info.show().text(this.model.get('info')) : this.$info.hide();
	            this.model.get('value') ? this.$text.text(this.model.get('value')).show() : this.$text.hide();
	            this.model.get('wait') ? this.$wait.show() : this.$wait.hide();
	            return this;
	        },
	        _readFile: function (e) {
	            var self = this;
	            var file = e.target.files && e.target.files[0];
	            if (file) {
	                var reader = new FileReader();
	                reader.onload = function () {
	                    self.model.set({ wait: false, value: this.result });
	                };
	                this.model.set({ wait: true, value: null });
	                reader.readAsText(file);
	            }
	        }
	    });
	
	    return {
	        Button: Buttons.ButtonDefault,
	        ButtonIcon: Buttons.ButtonIcon,
	        ButtonCheck: Buttons.ButtonCheck,
	        ButtonMenu: Buttons.ButtonMenu,
	        ButtonLink: Buttons.ButtonLink,
	        Input: Input,
	        Label: Label,
	        Message: Message,
	        UnescapedMessage: UnescapedMessage,
	        Upload: Upload,
	        Modal: Modal,
	        RadioButton: Options.RadioButton,
	        Checkbox: Options.Checkbox,
	        Radio: Options.Radio,
	        Select: Select,
	        Hidden: Hidden,
	        Slider: Slider,
	        Drilldown: Drilldown
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 18 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $, _) {/**
	 *  This class creates/wraps a default html select field as backbone class.
	 */
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13), __webpack_require__(19)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils, Buttons) {
	    var View = Backbone.View.extend({
	        initialize: function (options) {
	            var self = this;
	            this.data = [];
	            this.data2 = [];
	            this.model = options && options.model || new Backbone.Model({
	                id: Utils.uid(),
	                cls: 'ui-select',
	                error_text: 'No options available',
	                empty_text: 'Nothing selected',
	                visible: true,
	                wait: false,
	                multiple: false,
	                searchable: true,
	                optional: false,
	                disabled: false,
	                onchange: function () {},
	                value: null,
	                selectall: true,
	                pagesize: 20
	            }).set(options);
	            this.on('change', function () {
	                self.model.get('onchange') && self.model.get('onchange')(self.value());
	            });
	            this.listenTo(this.model, 'change:data', this._changeData, this);
	            this.listenTo(this.model, 'change:disabled', this._changeDisabled, this);
	            this.listenTo(this.model, 'change:wait', this._changeWait, this);
	            this.listenTo(this.model, 'change:visible', this._changeVisible, this);
	            this.listenTo(this.model, 'change:value', this._changeValue, this);
	            this.listenTo(this.model, 'change:multiple change:searchable change:cls change:id', this.render, this);
	            this.render();
	        },
	
	        render: function () {
	            var self = this;
	            this.model.get('searchable') ? this._renderSearchable() : this._renderClassic();
	            this.$el.addClass(this.model.get('cls')).attr('id', this.model.get('id'));
	            this.$select.empty().addClass('select').attr('id', this.model.get('id') + '_select').prop('multiple', this.model.get('multiple')).on('change', function () {
	                self.value(self._getValue());
	                self.trigger('change');
	            });
	            this._changeData();
	            this._changeWait();
	            this._changeVisible();
	            this._changeDisabled();
	        },
	
	        /** Renders the classic selection field */
	        _renderClassic: function () {
	            var self = this;
	            this.$el.addClass(this.model.get('multiple') ? 'ui-select-multiple' : 'ui-select').append(this.$select = $('<select/>')).append(this.$dropdown = $('<div/>')).append(this.$resize = $('<div/>').append(this.$resize_icon = $('<i/>')));
	            if (this.model.get('multiple')) {
	                this.$dropdown.hide();
	                this.$resize_icon.addClass('fa fa-angle-double-right fa-rotate-45').show();
	                this.$resize.removeClass().addClass('icon-resize').show().off('mousedown').on('mousedown', function (event) {
	                    var currentY = event.pageY;
	                    var currentHeight = self.$select.height();
	                    self.minHeight = self.minHeight || currentHeight;
	                    $('#dd-helper').show().on('mousemove', function (event) {
	                        self.$select.height(Math.max(currentHeight + (event.pageY - currentY), self.minHeight));
	                    }).on('mouseup mouseleave', function () {
	                        $('#dd-helper').hide().off();
	                    });
	                });
	            } else {
	                this.$dropdown.show();
	                this.$resize.hide();
	                this.$resize_icon.hide();
	            }
	        },
	
	        /** Renders the default select2 field */
	        _renderSearchable: function () {
	            var self = this;
	            this.$el.append(this.$select = $('<div/>')).append(this.$dropdown = $('<div/>'));
	            this.$dropdown.hide();
	            if (!this.model.get('multiple')) {
	                this.$dropdown.show().on('click', function () {
	                    self.$select.select2 && self.$select.select2('open');
	                });
	            }
	            this.all_button = null;
	            if (this.model.get('multiple') && this.model.get('selectall')) {
	                this.all_button = new Buttons.ButtonCheck({
	                    onclick: function () {
	                        var new_value = [];
	                        self.all_button.value() !== 0 && _.each(self.model.get('data'), function (option) {
	                            new_value.push(option.value);
	                        });
	                        self.value(new_value);
	                        self.trigger('change');
	                    }
	                });
	                this.$el.prepend(this.all_button.$el);
	            }
	        },
	
	        /** Matches a search term with a given text */
	        _match: function (term, text) {
	            return !term || term == '' || String(text).toUpperCase().indexOf(term.toUpperCase()) >= 0;
	        },
	
	        /** Updates the selection options */
	        _changeData: function () {
	            var self = this;
	            this.data = [];
	            if (!this.model.get('multiple') && this.model.get('optional')) {
	                this.data.push({ value: '__null__', label: self.model.get('empty_text') });
	            }
	            _.each(this.model.get('data'), function (option) {
	                self.data.push(option);
	            });
	            if (this.length() == 0) {
	                this.data.push({ value: '__null__', label: this.model.get('error_text') });
	            }
	            if (this.model.get('searchable')) {
	                this.data2 = [];
	                _.each(this.data, function (option, index) {
	                    self.data2.push({ order: index, id: option.value, text: option.label, tags: option.tags });
	                });
	                this.$select.data('select2') && this.$select.select2('destroy');
	                this.matched_tags = {};
	                this.$select.select2({
	                    data: self.data2,
	                    closeOnSelect: !this.model.get('multiple'),
	                    multiple: this.model.get('multiple'),
	                    query: function (q) {
	                        self.matched_tags = {};
	                        var pagesize = self.model.get('pagesize');
	                        var results = _.filter(self.data2, function (e) {
	                            var found = false;
	                            _.each(e.tags, function (tag) {
	                                if (self._match(q.term, tag)) {
	                                    found = self.matched_tags[tag] = true;
	                                }
	                            });
	                            return found || self._match(q.term, e.text);
	                        });
	                        q.callback({
	                            results: results.slice((q.page - 1) * pagesize, q.page * pagesize),
	                            more: results.length >= q.page * pagesize
	                        });
	                    },
	                    formatResult: function (result) {
	                        return _.escape(result.text) + '<div class="ui-tags">' + _.reduce(result.tags, function (memo, tag) {
	                            if (self.matched_tags[tag]) {
	                                return memo + '&nbsp;' + '<div class="label label-info">' + _.escape(tag) + '</div>';
	                            }
	                            return memo;
	                        }, '') + '</div>';
	                    }
	                });
	                this.$('.select2-container .select2-search input').off('blur');
	            } else {
	                this.$select.find('option').remove();
	                _.each(this.data, function (option) {
	                    self.$select.append($('<option/>').attr('value', option.value).html(_.escape(option.label)));
	                });
	            }
	            this.model.set('disabled', this.length() == 0);
	            this._changeValue();
	        },
	
	        /** Handles field enabling/disabling, usually used when no options are available */
	        _changeDisabled: function () {
	            if (this.model.get('searchable')) {
	                this.$select.select2(this.model.get('disabled') ? 'disable' : 'enable');
	            } else {
	                this.$select.prop('disabled', this.model.get('disabled'));
	            }
	        },
	
	        /** Searchable fields may display a spinner e.g. while waiting for a server response */
	        _changeWait: function () {
	            this.$dropdown.removeClass().addClass('icon-dropdown fa').addClass(this.model.get('wait') ? 'fa-spinner fa-spin' : 'fa-caret-down');
	        },
	
	        /** Handles field visibility */
	        _changeVisible: function () {
	            this.$el[this.model.get('visible') ? 'show' : 'hide']();
	            this.$select[this.model.get('visible') ? 'show' : 'hide']();
	        },
	
	        /** Synchronizes the model value with the actually selected field value */
	        _changeValue: function () {
	            this._setValue(this.model.get('value'));
	            if (this.model.get('multiple')) {
	                if (this.all_button) {
	                    var value = this._getValue();
	                    this.all_button.value($.isArray(value) ? value.length : 0, this.length());
	                }
	            } else if (this._getValue() === null && !this.model.get('optional')) {
	                this._setValue(this.first());
	            }
	        },
	
	        /** Return/Set current selection */
	        value: function (new_value) {
	            new_value !== undefined && this.model.set('value', new_value);
	            return this._getValue();
	        },
	
	        /** Return the first select option */
	        first: function () {
	            return this.data.length > 0 ? this.data[0].value : null;
	        },
	
	        /** Check if a value is an existing option */
	        exists: function (value) {
	            return _.findWhere(this.data, { value: value });
	        },
	
	        /** Return the label/text of the current selection */
	        text: function () {
	            var v = this._getValue();
	            var d = this.exists($.isArray(v) ? v[0] : v);
	            return d ? d.label : '';
	        },
	
	        /** Show the select field */
	        show: function () {
	            this.model.set('visible', true);
	        },
	
	        /** Hide the select field */
	        hide: function () {
	            this.model.set('visible', false);
	        },
	
	        /** Show a spinner indicating that the select options are currently loaded */
	        wait: function () {
	            this.model.set('wait', true);
	        },
	
	        /** Hide spinner indicating that the request has been completed */
	        unwait: function () {
	            this.model.set('wait', false);
	        },
	
	        /** Returns true if the field is disabled */
	        disabled: function () {
	            return this.model.get('disabled');
	        },
	
	        /** Enable the select field */
	        enable: function () {
	            this.model.set('disabled', false);
	        },
	
	        /** Disable the select field */
	        disable: function () {
	            this.model.set('disabled', true);
	        },
	
	        /** Update all available options at once */
	        add: function (options, sorter) {
	            _.each(this.model.get('data'), function (v) {
	                v.keep && !_.findWhere(options, { value: v.value }) && options.push(v);
	            });
	            sorter && options && options.sort(sorter);
	            this.model.set('data', options);
	        },
	
	        /** Update available options */
	        update: function (options) {
	            this.model.set('data', options);
	        },
	
	        /** Set the custom onchange callback function */
	        setOnChange: function (callback) {
	            this.model.set('onchange', callback);
	        },
	
	        /** Number of available options */
	        length: function () {
	            return $.isArray(this.model.get('data')) ? this.model.get('data').length : 0;
	        },
	
	        /** Set value to dom */
	        _setValue: function (new_value) {
	            var self = this;
	            if (new_value === null || new_value === undefined) {
	                new_value = '__null__';
	            }
	            if (this.model.get('multiple')) {
	                new_value = $.isArray(new_value) ? new_value : [new_value];
	            } else if ($.isArray(new_value)) {
	                if (new_value.length > 0) {
	                    new_value = new_value[0];
	                } else {
	                    new_value = '__null__';
	                }
	            }
	            if (this.model.get('searchable')) {
	                if ($.isArray(new_value)) {
	                    val = [];
	                    _.each(new_value, function (v) {
	                        var d = _.findWhere(self.data2, { id: v });
	                        d && val.push(d);
	                    });
	                    new_value = val;
	                } else {
	                    var d = _.findWhere(this.data2, { id: new_value });
	                    new_value = d;
	                }
	                this.$select.select2('data', new_value);
	            } else {
	                this.$select.val(new_value);
	            }
	        },
	
	        /** Get value from dom */
	        _getValue: function () {
	            var val = null;
	            if (this.model.get('searchable')) {
	                var selected = this.$select.select2('data');
	                if (selected) {
	                    if ($.isArray(selected)) {
	                        val = [];
	                        selected.sort(function (a, b) {
	                            return a.order - b.order;
	                        });
	                        _.each(selected, function (v) {
	                            val.push(v.id);
	                        });
	                    } else {
	                        val = selected.id;
	                    }
	                }
	            } else {
	                val = this.$select.val();
	            }
	            return Utils.isEmpty(val) ? null : val;
	        }
	    });
	
	    return {
	        View: View
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 19 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $) {/** This module contains all button views. */
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils) {
	    /** This renders the default button which is used e.g. at the bottom of the upload modal. */
	    var ButtonDefault = Backbone.View.extend({
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model({
	                id: Utils.uid(),
	                title: '',
	                floating: 'right',
	                icon: '',
	                cls: 'btn btn-default',
	                wait: false,
	                wait_text: 'Sending...',
	                wait_cls: 'btn btn-info',
	                disabled: false,
	                percentage: -1
	            }).set(options);
	            this.setElement($('<button/>').attr('type', 'button').append(this.$icon = $('<i/>')).append(this.$title = $('<span/>')).append(this.$progress = $('<div/>').append(this.$progress_bar = $('<div/>'))));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	
	        render: function () {
	            var self = this;
	            var options = this.model.attributes;
	            this.$el.removeClass().addClass('ui-button-default').addClass(options.disabled && 'disabled').attr('id', options.id).attr('disabled', options.disabled).css('float', options.floating).off('click').on('click', function () {
	                $('.tooltip').hide();
	                options.onclick && !self.disabled && options.onclick();
	            }).tooltip({ title: options.tooltip, placement: 'bottom' });
	            this.$progress.addClass('progress').css('display', options.percentage !== -1 ? 'block' : 'none');
	            this.$progress_bar.addClass('progress-bar').css({ width: options.percentage + '%' });
	            this.$icon.removeClass().addClass('icon fa');
	            this.$title.removeClass().addClass('title');
	            if (options.wait) {
	                this.$el.addClass(options.wait_cls).prop('disabled', true);
	                this.$icon.addClass('fa-spinner fa-spin ui-margin-right');
	                this.$title.html(options.wait_text);
	            } else {
	                this.$el.addClass(options.cls);
	                this.$icon.addClass(options.icon);
	                this.$title.html(options.title);
	                options.icon && options.title && this.$icon.addClass('ui-margin-right');
	            }
	        },
	
	        /** Show button */
	        show: function () {
	            this.$el.show();
	        },
	
	        /** Hide button */
	        hide: function () {
	            this.$el.hide();
	        },
	
	        /** Disable button */
	        disable: function () {
	            this.model.set('disabled', true);
	        },
	
	        /** Enable button */
	        enable: function () {
	            this.model.set('disabled', false);
	        },
	
	        /** Show spinner to indicate that the button is not ready to be clicked */
	        wait: function () {
	            this.model.set('wait', true);
	        },
	
	        /** Hide spinner to indicate that the button is ready to be clicked */
	        unwait: function () {
	            this.model.set('wait', false);
	        },
	
	        /** Change icon */
	        setIcon: function (icon) {
	            this.model.set('icon', icon);
	        }
	    });
	
	    /** This button allows the right-click/open-in-new-tab feature, its used e.g. for panel buttons. */
	    var ButtonLink = ButtonDefault.extend({
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model({
	                id: Utils.uid(),
	                title: '',
	                icon: '',
	                cls: ''
	            }).set(options);
	            this.setElement($('<a/>').append(this.$icon = $('<span/>')));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	
	        render: function () {
	            var options = this.model.attributes;
	            this.$el.removeClass().addClass(options.cls).attr({ id: options.id,
	                href: options.href || 'javascript:void(0)',
	                title: options.title,
	                target: options.target || '_top',
	                disabled: options.disabled }).tooltip({ placement: 'bottom' }).off('click').on('click', function () {
	                options.onclick && !options.disabled && options.onclick();
	            });
	            this.$icon.removeClass().addClass(options.icon);
	        }
	    });
	
	    /** The check button is used in the tool form and allows to distinguish between multiple states e.g. all, partially and nothing selected. */
	    var ButtonCheck = Backbone.View.extend({
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model({
	                id: Utils.uid(),
	                title: 'Select/Unselect all',
	                icons: ['fa-square-o', 'fa-minus-square-o', 'fa-check-square-o'],
	                value: 0,
	                onchange: function () {}
	            }).set(options);
	            this.setElement($('<div/>').append(this.$icon = $('<span/>')).append(this.$title = $('<span/>')));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	
	        render: function (options) {
	            var self = this;
	            var options = this.model.attributes;
	            this.$el.addClass('ui-button-check').off('click').on('click', function () {
	                self.model.set('value', self.model.get('value') === 0 && 2 || 0);
	                options.onclick && options.onclick();
	            });
	            this.$title.html(options.title);
	            this.$icon.removeClass().addClass('icon fa ui-margin-right').addClass(options.icons[options.value]);
	        },
	
	        /* Sets a new value and/or returns the value.
	        * @param{Integer}   new_val - Set a new value 0=unchecked, 1=partial and 2=checked.
	        * OR:
	        * @param{Integer}   new_val - Number of selected options.
	        * @param{Integer}   total   - Total number of available options.
	        */
	        value: function (new_val, total) {
	            if (new_val !== undefined) {
	                if (total && new_val !== 0) {
	                    new_val = new_val !== total && 1 || 2;
	                }
	                this.model.set('value', new_val);
	                this.model.get('onchange')(this.model.get('value'));
	            }
	            return this.model.get('value');
	        }
	    });
	
	    /** This renders a differently styled, more compact button version. */
	    var ButtonIcon = ButtonDefault.extend({
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model({
	                id: Utils.uid(),
	                title: '',
	                floating: 'right',
	                icon: '',
	                cls: 'ui-button-icon',
	                disabled: false
	            }).set(options);
	            this.setElement($('<div/>').append(this.$button = $('<div/>').append(this.$icon = $('<i/>')).append(this.$title = $('<span/>'))));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	
	        render: function (options) {
	            var self = this;
	            var options = this.model.attributes;
	            this.$el.removeClass().addClass(options.cls).addClass(options.disabled && 'disabled').attr('disabled', options.disabled).attr('id', options.id).css('float', options.floating).off('click').on('click', function () {
	                $('.tooltip').hide();
	                !options.disabled && options.onclick && options.onclick();
	            });
	            this.$button.addClass('button').tooltip({ title: options.tooltip, placement: 'bottom' });
	            this.$icon.removeClass().addClass('icon fa').addClass(options.icon);
	            this.$title.addClass('title').html(options.title);
	            options.icon && options.title && this.$icon.addClass('ui-margin-right');
	        }
	    });
	
	    /** This class creates a button with dropdown menu. */
	    var ButtonMenu = ButtonDefault.extend({
	        $menu: null,
	        initialize: function (options) {
	            this.model = options && options.model || new Backbone.Model({
	                id: '',
	                title: '',
	                floating: 'right',
	                pull: 'right',
	                icon: null,
	                onclick: null,
	                cls: 'ui-button-icon ui-button-menu',
	                tooltip: '',
	                target: '',
	                href: '',
	                onunload: null,
	                visible: true,
	                tag: ''
	            }).set(options);
	            this.collection = new Backbone.Collection();
	            this.setElement($('<div/>').append(this.$root = $('<div/>').append(this.$icon = $('<i/>')).append(this.$title = $('<span/>'))));
	            this.listenTo(this.model, 'change', this.render, this);
	            this.listenTo(this.collection, 'change add remove reset', this.render, this);
	            this.render();
	        },
	
	        render: function () {
	            var self = this;
	            var options = this.model.attributes;
	            this.$el.removeClass().addClass('dropdown').addClass(options.cls).attr('id', options.id).css({ float: options.floating,
	                display: options.visible && this.collection.where({ visible: true }).length > 0 ? 'block' : 'none' });
	            this.$root.addClass('root button dropdown-toggle').attr('data-toggle', 'dropdown').tooltip({ title: options.tooltip, placement: 'bottom' }).off('click').on('click', function (e) {
	                $('.tooltip').hide();
	                e.preventDefault();
	                options.onclick && options.onclick();
	            });
	            this.$icon.removeClass().addClass('icon fa').addClass(options.icon);
	            this.$title.removeClass().addClass('title').html(options.title);
	            options.icon && options.title && this.$icon.addClass('ui-margin-right');
	            this.$menu && this.$menu.remove();
	            if (this.collection.length > 0) {
	                this.$menu = $('<ul/>').addClass('menu dropdown-menu').addClass('pull-' + self.model.get('pull')).attr('role', 'menu');
	                this.$el.append(this.$menu);
	            }
	            this.collection.each(function (submodel) {
	                var suboptions = submodel.attributes;
	                if (suboptions.visible) {
	                    var $link = $('<a/>').addClass('dropdown-item').attr({ href: suboptions.href, target: suboptions.target }).append($('<i/>').addClass('fa').addClass(suboptions.icon).css('display', suboptions.icon ? 'inline-block' : 'none')).append(suboptions.title).on('click', function (e) {
	                        if (suboptions.onclick) {
	                            e.preventDefault();
	                            suboptions.onclick();
	                        }
	                    });
	                    self.$menu.append($('<li/>').append($link));
	                    suboptions.divider && self.$menu.append($('<li/>').addClass('divider'));
	                }
	            });
	        },
	
	        /** Add a new menu item */
	        addMenu: function (options) {
	            this.collection.add(Utils.merge(options, {
	                title: '',
	                target: '',
	                href: '',
	                onclick: null,
	                divider: false,
	                visible: true,
	                icon: null,
	                cls: 'button-menu btn-group'
	            }));
	        }
	    });
	
	    return {
	        ButtonDefault: ButtonDefault,
	        ButtonLink: ButtonLink,
	        ButtonIcon: ButtonIcon,
	        ButtonCheck: ButtonCheck,
	        ButtonMenu: ButtonMenu
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(3)))

/***/ },
/* 20 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $) {!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils) {
	    var View = Backbone.View.extend({
	        initialize: function (options) {
	            var self = this;
	            this.model = options && options.model || new Backbone.Model({
	                id: Utils.uid(),
	                min: null,
	                max: null,
	                step: null,
	                precise: false,
	                split: 10000,
	                value: null,
	                onchange: function () {}
	            }).set(options);
	
	            // create new element
	            this.setElement(this._template());
	            this.$el.attr('id', this.model.id);
	            this.$text = this.$('.ui-form-slider-text');
	            this.$slider = this.$('.ui-form-slider-element');
	
	            // add text field event
	            var pressed = [];
	            this.$text.on('change', function () {
	                self.value($(this).val());
	            }).on('keyup', function (e) {
	                pressed[e.which] = false;
	            }).on('keydown', function (e) {
	                var v = e.which;
	                pressed[v] = true;
	                if (self.model.get('is_workflow') && pressed[16] && v == 52) {
	                    self.value('$');
	                    event.preventDefault();
	                } else if (!(v == 8 || v == 9 || v == 13 || v == 37 || v == 39 || v >= 48 && v <= 57 && !pressed[16] || v >= 96 && v <= 105 || (v == 190 || v == 110) && $(this).val().indexOf('.') == -1 && self.model.get('precise') || (v == 189 || v == 109) && $(this).val().indexOf('-') == -1 || self._isParameter($(this).val()) || pressed[91] || pressed[17])) {
	                    event.preventDefault();
	                }
	            });
	
	            // build slider, cannot be rebuild in render
	            var opts = this.model.attributes;
	            this.has_slider = opts.max !== null && opts.min !== null && opts.max > opts.min;
	            var step = opts.step;
	            if (!step) {
	                if (opts.precise && this.has_slider) {
	                    step = (opts.max - opts.min) / opts.split;
	                } else {
	                    step = 1.0;
	                }
	            }
	            if (this.has_slider) {
	                this.$text.addClass('ui-form-slider-left');
	                this.$slider.slider({ min: opts.min, max: opts.max, step: step }).on('slide', function (event, ui) {
	                    self.value(ui.value);
	                });
	            } else {
	                this.$slider.hide();
	            }
	
	            // add listeners
	            this.listenTo(this.model, 'change', this.render, this);
	            this.render();
	        },
	
	        render: function () {
	            var value = this.model.get('value');
	            this.has_slider && this.$slider.slider('value', value);
	            value !== this.$text.val() && this.$text.val(value);
	        },
	
	        /** Set and return the current value */
	        value: function (new_val) {
	            var options = this.model.attributes;
	            if (new_val !== undefined) {
	                if (new_val !== null && new_val !== '' && !this._isParameter(new_val)) {
	                    isNaN(new_val) && (new_val = 0);
	                    !options.precise && (new_val = Math.round(new_val));
	                    options.max !== null && (new_val = Math.min(new_val, options.max));
	                    options.min !== null && (new_val = Math.max(new_val, options.min));
	                }
	                this.model.set('value', new_val);
	                this.model.trigger('change');
	                options.onchange(new_val);
	            }
	            return this.model.get('value');
	        },
	
	        /** Return true if the field contains a workflow parameter i.e. $('name') */
	        _isParameter: function (value) {
	            return this.model.get('is_workflow') && String(value).substring(0, 1) === '$';
	        },
	
	        /** Slider template */
	        _template: function () {
	            return '<div class="ui-form-slider">' + '<input class="ui-form-slider-text" type="text"/>' + '<div class="ui-form-slider-element"/>' + '</div>';
	        }
	    });
	
	    return {
	        View: View
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(3)))

/***/ },
/* 21 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(Backbone, $, _) {/** Base class for options based ui elements **/
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13), __webpack_require__(19)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils, Buttons) {
	    var Base = Backbone.View.extend({
	        initialize: function (options) {
	            var self = this;
	            this.model = options && options.model || new Backbone.Model({
	                visible: true,
	                data: [],
	                id: Utils.uid(),
	                error_text: 'No options available.',
	                wait_text: 'Please wait...',
	                multiple: false,
	                optional: false,
	                onchange: function () {}
	            }).set(options);
	            this.listenTo(this.model, 'change:value', this._changeValue, this);
	            this.listenTo(this.model, 'change:wait', this._changeWait, this);
	            this.listenTo(this.model, 'change:data', this._changeData, this);
	            this.listenTo(this.model, 'change:visible', this._changeVisible, this);
	            this.on('change', function () {
	                self.model.get('onchange')(self.value());
	            });
	            this.render();
	        },
	
	        render: function () {
	            var self = this;
	            this.$el.empty().removeClass().addClass('ui-options').append(this.$message = $('<div/>')).append(this.$menu = $('<div/>').addClass('ui-options-menu')).append(this.$options = $(this._template()));
	
	            // add select/unselect all button
	            this.all_button = null;
	            if (this.model.get('multiple')) {
	                this.all_button = new Buttons.ButtonCheck({
	                    onclick: function () {
	                        self.$('input').prop('checked', self.all_button.value() !== 0);
	                        self.value(self._getValue());
	                        self.trigger('change');
	                    }
	                });
	                this.$menu.append(this.all_button.$el);
	            }
	
	            // finalize dom
	            this._changeData();
	            this._changeWait();
	            this._changeVisible();
	        },
	
	        /** Update available options */
	        update: function (options) {
	            this.model.set('data', options);
	        },
	
	        _changeData: function () {
	            var self = this;
	            this.$options.empty();
	            if (this._templateOptions) {
	                this.$options.append(this._templateOptions(this.model.get('data')));
	            } else {
	                _.each(this.model.get('data'), function (option) {
	                    self.$options.append($(self._templateOption(option)).addClass('ui-option').tooltip({ title: option.tooltip, placement: 'bottom' }));
	                });
	            }
	            var self = this;
	            this.$('input').on('change', function () {
	                self.value(self._getValue());
	                self.trigger('change');
	            });
	            this._changeValue();
	            this._changeWait();
	        },
	
	        _changeVisible: function () {
	            this.$el[this.model.get('visible') ? 'show' : 'hide']();
	        },
	
	        _changeWait: function () {
	            if (this.model.get('wait')) {
	                if (this.length() === 0) {
	                    this._messageShow(this.model.get('wait_text'), 'info');
	                    this.$options.hide();
	                    this.$menu.hide();
	                }
	            } else {
	                if (this.length() === 0) {
	                    this._messageShow(this.model.get('error_text'), 'danger');
	                    this.$options.hide();
	                    this.$menu.hide();
	                } else {
	                    this.$message.hide();
	                    this.$options.css('display', 'inline-block');
	                    this.$menu.show();
	                }
	            }
	        },
	
	        _changeValue: function () {
	            this._setValue(this.model.get('value'));
	            if (this._getValue() === null && !this.model.get('multiple') && !this.model.get('optional')) {
	                this._setValue(this.first());
	            }
	            this.all_button && this.all_button.value($.isArray(this._getValue()) ? this._getValue().length : 0, this.length());
	        },
	
	        /** Return/Set current selection */
	        value: function (new_value) {
	            new_value !== undefined && this.model.set('value', new_value);
	            return this._getValue();
	        },
	
	        /** Return first available option */
	        first: function () {
	            var options = this.$('input').first();
	            return options.length > 0 ? options.val() : null;
	        },
	
	        /** Show a spinner indicating that the select options are currently loaded */
	        wait: function () {
	            this.model.set('wait', true);
	        },
	
	        /** Hide spinner indicating that the request has been completed */
	        unwait: function () {
	            this.model.set('wait', false);
	        },
	
	        /** Returns the number of options */
	        length: function () {
	            return this.$('.ui-option').length;
	        },
	
	        /** Set value to dom */
	        _setValue: function (new_value) {
	            var self = this;
	            if (new_value !== undefined) {
	                this.$('input').prop('checked', false);
	                if (new_value !== null) {
	                    var values = $.isArray(new_value) ? new_value : [new_value];
	                    _.each(values, function (v) {
	                        self.$('input[value="' + v + '"]').first().prop('checked', true);
	                    });
	                }
	            }
	        },
	
	        /** Return current selection */
	        _getValue: function () {
	            var selected = [];
	            this.$(':checked').each(function () {
	                selected.push($(this).val());
	            });
	            if (Utils.isEmpty(selected)) {
	                return null;
	            }
	            return this.model.get('multiple') ? selected : selected[0];
	        },
	
	        /** Show message instead if options */
	        _messageShow: function (text, status) {
	            this.$message.show().removeClass().addClass('ui-message alert alert-' + status).html(text);
	        },
	
	        /** Main template function */
	        _template: function () {
	            return $('<div/>').addClass('ui-options-list');
	        }
	    });
	
	    /** Iconized **/
	    var BaseIcons = Base.extend({
	        _templateOption: function (pair) {
	            var id = Utils.uid();
	            return $('<div/>').addClass('ui-option').append($('<input/>').attr({
	                id: id,
	                type: this.model.get('type'),
	                name: this.model.id,
	                value: pair.value })).append($('<label/>').addClass('ui-options-label').attr('for', id).html(pair.label));
	        }
	    });
	
	    /** Radio button field **/
	    var Radio = {};
	    Radio.View = BaseIcons.extend({
	        initialize: function (options) {
	            options.type = 'radio';
	            BaseIcons.prototype.initialize.call(this, options);
	        }
	    });
	
	    /** Checkbox options field **/
	    var Checkbox = {};
	    Checkbox.View = BaseIcons.extend({
	        initialize: function (options) {
	            options.type = 'checkbox';
	            options.multiple = true;
	            BaseIcons.prototype.initialize.call(this, options);
	        }
	    });
	
	    /** Radio button options field styled as classic buttons **/
	    var RadioButton = {};
	    RadioButton.View = Base.extend({
	        initialize: function (options) {
	            Base.prototype.initialize.call(this, options);
	        },
	
	        /** Set current value */
	        _setValue: function (new_value) {
	            if (new_value !== undefined) {
	                this.$('input').prop('checked', false);
	                this.$('label').removeClass('active');
	                this.$('[value="' + new_value + '"]').prop('checked', true).closest('label').addClass('active');
	            }
	        },
	
	        /** Template for a single option */
	        _templateOption: function (pair) {
	            var $el = $('<label/>').addClass('btn btn-default');
	            pair.icon && $el.append($('<i/>').addClass('fa').addClass(pair.icon).addClass(!pair.label && 'no-padding'));
	            $el.append($('<input/>').attr({ type: 'radio', name: this.model.id, value: pair.value }));
	            pair.label && $el.append(pair.label);
	            return $el;
	        },
	
	        /** Main template function */
	        _template: function () {
	            return $('<div/>').addClass('btn-group ui-radiobutton').attr('data-toggle', 'buttons');
	        }
	    });
	
	    return {
	        Base: Base,
	        BaseIcons: BaseIcons,
	        Radio: Radio,
	        RadioButton: RadioButton,
	        Checkbox: Checkbox
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2), __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 22 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_ARRAY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function($, _) {/** This class creates/wraps a drill down element. */
	!(__WEBPACK_AMD_DEFINE_ARRAY__ = [__webpack_require__(13), __webpack_require__(21)], __WEBPACK_AMD_DEFINE_RESULT__ = function (Utils, Options) {
	
	    var View = Options.BaseIcons.extend({
	        initialize: function (options) {
	            options.type = options.display || 'checkbox';
	            options.multiple = options.type == 'checkbox';
	            Options.BaseIcons.prototype.initialize.call(this, options);
	        },
	
	        /** Set states for selected values */
	        _setValue: function (new_value) {
	            Options.BaseIcons.prototype._setValue.call(this, new_value);
	            if (new_value !== undefined && new_value !== null && this.header_index) {
	                var self = this;
	                var values = $.isArray(new_value) ? new_value : [new_value];
	                _.each(values, function (v) {
	                    var list = self.header_index[v];
	                    _.each(list, function (element) {
	                        self._setState(element, true);
	                    });
	                });
	            }
	        },
	
	        /** Expand/collapse a sub group */
	        _setState: function (header_id, is_expanded) {
	            var $button = this.$('.button-' + header_id);
	            var $subgroup = this.$('.subgroup-' + header_id);
	            $button.data('is_expanded', is_expanded);
	            if (is_expanded) {
	                $subgroup.show();
	                $button.removeClass('fa-plus-square').addClass('fa-minus-square');
	            } else {
	                $subgroup.hide();
	                $button.removeClass('fa-minus-square').addClass('fa-plus-square');
	            }
	        },
	
	        /** Template to create options tree */
	        _templateOptions: function () {
	            var self = this;
	            this.header_index = {};
	
	            // attach event handler
	            function attach($el, header_id) {
	                var $button = $el.find('.button-' + header_id);
	                $button.on('click', function () {
	                    self._setState(header_id, !$button.data('is_expanded'));
	                });
	            }
	
	            // recursive function which iterates through options
	            function iterate($tmpl, options, header) {
	                header = header || [];
	                for (i in options) {
	                    var level = options[i];
	                    var has_options = level.options && level.options.length > 0;
	                    var new_header = header.slice(0);
	                    self.header_index[level.value] = new_header.slice(0);
	                    var $group = $('<div/>');
	                    if (has_options) {
	                        var header_id = Utils.uid();
	                        var $button = $('<span/>').addClass('button-' + header_id).addClass('ui-drilldown-button fa fa-plus-square');
	                        var $subgroup = $('<div/>').addClass('subgroup-' + header_id).addClass('ui-drilldown-subgroup');
	                        $group.append($('<div/>').append($button).append(self._templateOption({ label: level.name, value: level.value })));
	                        new_header.push(header_id);
	                        iterate($subgroup, level.options, new_header);
	                        $group.append($subgroup);
	                        attach($group, header_id);
	                    } else {
	                        $group.append(self._templateOption({ label: level.name, value: level.value }));
	                    }
	                    $tmpl.append($group);
	                }
	            }
	
	            // iterate through options and create dom
	            var $tmpl = $('<div/>');
	            iterate($tmpl, this.model.get('data'));
	            return $tmpl;
	        },
	
	        /** Template for drill down view */
	        _template: function () {
	            return $('<div/>').addClass('ui-options-list drilldown-container').attr('id', this.model.id);
	        }
	    });
	
	    return {
	        View: View
	    };
	}.apply(exports, __WEBPACK_AMD_DEFINE_ARRAY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__));
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 23 */,
/* 24 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(Backbone) {var jQuery = __webpack_require__(3),
	    $ = jQuery,
	    QUERY_STRING = __webpack_require__(25),
	    Ui = __webpack_require__(17);
	
	var Router = Backbone.Router.extend({
	    // TODO: not many client routes at this point - fill and remove from server.
	    // since we're at root here, this may be the last to be routed entirely on the client.
	    initialize: function (page, options) {
	        this.page = page;
	        this.options = options;
	    },
	
	    /** helper to push a new navigation state */
	    push: function (url, data) {
	        data = data || {};
	        data.__identifer = Math.random().toString(36).substr(2);
	        if (!$.isEmptyObject(data)) {
	            url += url.indexOf('?') == -1 ? '?' : '&';
	            url += $.param(data, true);
	        }
	        this.navigate(url, { 'trigger': true });
	    },
	
	    /** override to parse query string into obj and send to each route */
	    execute: function (callback, args, name) {
	        Galaxy.debug('router execute:', callback, args, name);
	        var queryObj = QUERY_STRING.parse(args.pop());
	        args.push(queryObj);
	        if (callback) {
	            if (this.authenticate(args, name)) {
	                callback.apply(this, args);
	            } else {
	                this.access_denied();
	            }
	        }
	    },
	
	    authenticate: function (args, name) {
	        return true;
	    },
	
	    access_denied: function () {
	        this.page.display(new Ui.Message({ status: 'danger', message: 'You must be logged in with proper credentials to make this request.', persistent: true }));
	    }
	});
	
	module.exports = Router;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(2)))

/***/ }
]);
//# sourceMappingURL=admin.bundled.js.map