define([ "libs/underscore", "viz/trackster/util", "mvc/data", "mvc/tools/tools-form", "templates/compiled/tool_form", "templates/compiled/tool_link", "templates/compiled/panel_section", "templates/compiled/tool_search" ], function(_, util, data, ToolsForm, tool_form, tool_link, panel_section, tool_search) {
    console.debug(tool_form, tool_link, panel_section, tool_search);
    var _templates = {
        tool_form: tool_form ? tool_form.Handlebars.templates.tool_form : Handlebars.templates.tool_form,
        tool_link: tool_link ? tool_link.Handlebars.templates.tool_link : Handlebars.templates.tool_link,
        panel_section: panel_section ? panel_section.Handlebars.templates.panel_section : Handlebars.templates.panel_section,
        tool_search: tool_search ? tool_search.Handlebars.templates.tool_search : Handlebars.templates.tool_search
    }, VisibilityMixin = {
        hidden: !1,
        show: function() {
            this.set("hidden", !1);
        },
        hide: function() {
            this.set("hidden", !0);
        },
        toggle: function() {
            this.set("hidden", !this.get("hidden"));
        },
        is_visible: function() {
            return !this.attributes.hidden;
        }
    }, ToolParameter = Backbone.Model.extend({
        defaults: {
            name: null,
            label: null,
            type: null,
            value: null,
            html: null,
            num_samples: 5
        },
        initialize: function() {
            this.attributes.html = unescape(this.attributes.html);
        },
        copy: function() {
            return new ToolParameter(this.toJSON());
        },
        set_value: function(value) {
            this.set("value", value || "");
        }
    }), ToolParameterCollection = Backbone.Collection.extend({
        model: ToolParameter
    }), DataToolParameter = ToolParameter.extend({}), IntegerToolParameter = ToolParameter.extend({
        set_value: function(value) {
            this.set("value", parseInt(value, 10));
        },
        get_samples: function() {
            return d3.scale.linear().domain([ this.get("min"), this.get("max") ]).ticks(this.get("num_samples"));
        }
    }), FloatToolParameter = IntegerToolParameter.extend({
        set_value: function(value) {
            this.set("value", parseFloat(value));
        }
    }), SelectToolParameter = ToolParameter.extend({
        get_samples: function() {
            return _.map(this.get("options"), function(option) {
                return option[0];
            });
        }
    });
    ToolParameter.subModelTypes = {
        integer: IntegerToolParameter,
        "float": FloatToolParameter,
        data: DataToolParameter,
        select: SelectToolParameter
    };
    var Tool = Backbone.Model.extend({
        defaults: {
            id: null,
            name: null,
            description: null,
            target: null,
            inputs: [],
            outputs: []
        },
        urlRoot: galaxy_config.root + "api/tools",
        initialize: function(options) {
            this.set("inputs", new ToolParameterCollection(_.map(options.inputs, function(p) {
                var p_class = ToolParameter.subModelTypes[p.type] || ToolParameter;
                return new p_class(p);
            })));
        },
        toJSON: function() {
            var rval = Backbone.Model.prototype.toJSON.call(this);
            return rval.inputs = this.get("inputs").map(function(i) {
                return i.toJSON();
            }), rval;
        },
        remove_inputs: function(types) {
            var tool = this, incompatible_inputs = tool.get("inputs").filter(function(input) {
                return -1 !== types.indexOf(input.get("type"));
            });
            tool.get("inputs").remove(incompatible_inputs);
        },
        copy: function(only_samplable_inputs) {
            var copy = new Tool(this.toJSON());
            if (only_samplable_inputs) {
                var valid_inputs = new Backbone.Collection();
                copy.get("inputs").each(function(input) {
                    input.get_samples() && valid_inputs.push(input);
                }), copy.set("inputs", valid_inputs);
            }
            return copy;
        },
        apply_search_results: function(results) {
            return -1 !== _.indexOf(results, this.attributes.id) ? this.show() : this.hide(), 
            this.is_visible();
        },
        set_input_value: function(name, value) {
            this.get("inputs").find(function(input) {
                return input.get("name") === name;
            }).set("value", value);
        },
        set_input_values: function(inputs_dict) {
            var self = this;
            _.each(_.keys(inputs_dict), function(input_name) {
                self.set_input_value(input_name, inputs_dict[input_name]);
            });
        },
        run: function() {
            return this._run();
        },
        rerun: function(target_dataset, regions) {
            return this._run({
                action: "rerun",
                target_dataset_id: target_dataset.id,
                regions: regions
            });
        },
        get_inputs_dict: function() {
            var input_dict = {};
            return this.get("inputs").each(function(input) {
                input_dict[input.get("name")] = input.get("value");
            }), input_dict;
        },
        _run: function(additional_params) {
            var payload = _.extend({
                tool_id: this.id,
                inputs: this.get_inputs_dict()
            }, additional_params), run_deferred = $.Deferred(), ss_deferred = new util.ServerStateDeferred({
                ajax_settings: {
                    url: this.urlRoot,
                    data: JSON.stringify(payload),
                    dataType: "json",
                    contentType: "application/json",
                    type: "POST"
                },
                interval: 2e3,
                success_fn: function(response) {
                    return "pending" !== response;
                }
            });
            return $.when(ss_deferred.go()).then(function(result) {
                run_deferred.resolve(new data.DatasetCollection(result));
            }), run_deferred;
        }
    });
    _.extend(Tool.prototype, VisibilityMixin);
    var ToolCollection = (Backbone.View.extend({}), Backbone.Collection.extend({
        model: Tool
    })), ToolSectionLabel = Backbone.Model.extend(VisibilityMixin), ToolSection = Backbone.Model.extend({
        defaults: {
            elems: [],
            open: !1
        },
        clear_search_results: function() {
            _.each(this.attributes.elems, function(elt) {
                elt.show();
            }), this.show(), this.set("open", !1);
        },
        apply_search_results: function(results) {
            var cur_label, all_hidden = !0;
            _.each(this.attributes.elems, function(elt) {
                elt instanceof ToolSectionLabel ? (cur_label = elt, cur_label.hide()) : elt instanceof Tool && elt.apply_search_results(results) && (all_hidden = !1, 
                cur_label && cur_label.show());
            }), all_hidden ? this.hide() : (this.show(), this.set("open", !0));
        }
    });
    _.extend(ToolSection.prototype, VisibilityMixin);
    var ToolSearch = Backbone.Model.extend({
        defaults: {
            search_hint_string: "search tools",
            min_chars_for_search: 3,
            spinner_url: "",
            clear_btn_url: "",
            search_url: "",
            visible: !0,
            query: "",
            results: null,
            clear_key: 27
        },
        urlRoot: galaxy_config.root + "api/tools",
        initialize: function() {
            this.on("change:query", this.do_search);
        },
        do_search: function() {
            var query = this.attributes.query;
            if (query.length < this.attributes.min_chars_for_search) return void this.set("results", null);
            var q = query;
            this.timer && clearTimeout(this.timer), $("#search-clear-btn").hide(), $("#search-spinner").show();
            var self = this;
            this.timer = setTimeout(function() {
                "undefined" != typeof ga && ga("send", "pageview", galaxy_config.root + "?q=" + q), 
                $.get(self.urlRoot, {
                    q: q
                }, function(data) {
                    self.set("results", data), $("#search-spinner").hide(), $("#search-clear-btn").show();
                }, "json");
            }, 400);
        },
        clear_search: function() {
            this.set("query", ""), this.set("results", null);
        }
    });
    _.extend(ToolSearch.prototype, VisibilityMixin);
    {
        var ToolPanel = Backbone.Model.extend({
            initialize: function(options) {
                this.attributes.tool_search = options.tool_search, this.attributes.tool_search.on("change:results", this.apply_search_results, this), 
                this.attributes.tools = options.tools, this.attributes.layout = new Backbone.Collection(this.parse(options.layout));
            },
            parse: function(response) {
                var self = this, parse_elt = function(elt_dict) {
                    var type = elt_dict.model_class;
                    if (type.indexOf("Tool") === type.length - 4) return self.attributes.tools.get(elt_dict.id);
                    if ("ToolSection" === type) {
                        var elems = _.map(elt_dict.elems, parse_elt);
                        return elt_dict.elems = elems, new ToolSection(elt_dict);
                    }
                    return "ToolSectionLabel" === type ? new ToolSectionLabel(elt_dict) : void 0;
                };
                return _.map(response, parse_elt);
            },
            clear_search_results: function() {
                this.get("layout").each(function(panel_elt) {
                    panel_elt instanceof ToolSection ? panel_elt.clear_search_results() : panel_elt.show();
                });
            },
            apply_search_results: function() {
                var results = this.get("tool_search").get("results");
                if (null === results) return void this.clear_search_results();
                var cur_label = null;
                this.get("layout").each(function(panel_elt) {
                    panel_elt instanceof ToolSectionLabel ? (cur_label = panel_elt, cur_label.hide()) : panel_elt instanceof Tool ? panel_elt.apply_search_results(results) && cur_label && cur_label.show() : (cur_label = null, 
                    panel_elt.apply_search_results(results));
                });
            }
        }), BaseView = Backbone.View.extend({
            initialize: function() {
                this.model.on("change:hidden", this.update_visible, this), this.update_visible();
            },
            update_visible: function() {
                this.model.attributes.hidden ? this.$el.hide() : this.$el.show();
            }
        }), ToolLinkView = BaseView.extend({
            tagName: "div",
            render: function() {
                var $link = $("<div/>");
                if ($link.append(_templates.tool_link(this.model.toJSON())), "upload1" === this.model.id && $link.find("a").on("click", function(e) {
                    e.preventDefault(), Galaxy.upload.show();
                }), "upload1" !== this.model.id && "Tool" === this.model.get("model_class")) {
                    var self = this;
                    $link.find("a").on("click", function(e) {
                        e.preventDefault();
                        var form = new ToolsForm.View({
                            id: self.model.id,
                            version: self.model.get("version")
                        });
                        form.deferred.execute(function() {
                            Galaxy.app.display(form.$el);
                        });
                    });
                }
                return this.$el.append($link), this;
            }
        }), ToolSectionLabelView = BaseView.extend({
            tagName: "div",
            className: "toolPanelLabel",
            render: function() {
                return this.$el.append($("<span/>").text(this.model.attributes.text)), this;
            }
        }), ToolSectionView = BaseView.extend({
            tagName: "div",
            className: "toolSectionWrapper",
            initialize: function() {
                BaseView.prototype.initialize.call(this), this.model.on("change:open", this.update_open, this);
            },
            render: function() {
                this.$el.append(_templates.panel_section(this.model.toJSON()));
                var section_body = this.$el.find(".toolSectionBody");
                return _.each(this.model.attributes.elems, function(elt) {
                    if (elt instanceof Tool) {
                        var tool_view = new ToolLinkView({
                            model: elt,
                            className: "toolTitle"
                        });
                        tool_view.render(), section_body.append(tool_view.$el);
                    } else if (elt instanceof ToolSectionLabel) {
                        var label_view = new ToolSectionLabelView({
                            model: elt
                        });
                        label_view.render(), section_body.append(label_view.$el);
                    }
                }), this;
            },
            events: {
                "click .toolSectionTitle > a": "toggle"
            },
            toggle: function() {
                this.model.set("open", !this.model.attributes.open);
            },
            update_open: function() {
                this.model.attributes.open ? this.$el.children(".toolSectionBody").slideDown("fast") : this.$el.children(".toolSectionBody").slideUp("fast");
            }
        }), ToolSearchView = Backbone.View.extend({
            tagName: "div",
            id: "tool-search",
            className: "bar",
            events: {
                click: "focus_and_select",
                "keyup :input": "query_changed",
                "click #search-clear-btn": "clear"
            },
            render: function() {
                return this.$el.append(_templates.tool_search(this.model.toJSON())), this.model.is_visible() || this.$el.hide(), 
                this.$el.find("[title]").tooltip(), this;
            },
            focus_and_select: function() {
                this.$el.find(":input").focus().select();
            },
            clear: function() {
                return this.model.clear_search(), this.$el.find(":input").val(""), this.focus_and_select(), 
                !1;
            },
            query_changed: function(evData) {
                return this.model.attributes.clear_key && this.model.attributes.clear_key === evData.which ? (this.clear(), 
                !1) : void this.model.set("query", this.$el.find(":input").val());
            }
        }), ToolPanelView = Backbone.View.extend({
            tagName: "div",
            className: "toolMenu",
            initialize: function() {
                this.model.get("tool_search").on("change:results", this.handle_search_results, this);
            },
            render: function() {
                var self = this, search_view = new ToolSearchView({
                    model: this.model.get("tool_search")
                });
                return search_view.render(), self.$el.append(search_view.$el), this.model.get("layout").each(function(panel_elt) {
                    if (panel_elt instanceof ToolSection) {
                        var section_title_view = new ToolSectionView({
                            model: panel_elt
                        });
                        section_title_view.render(), self.$el.append(section_title_view.$el);
                    } else if (panel_elt instanceof Tool) {
                        var tool_view = new ToolLinkView({
                            model: panel_elt,
                            className: "toolTitleNoSection"
                        });
                        tool_view.render(), self.$el.append(tool_view.$el);
                    } else if (panel_elt instanceof ToolSectionLabel) {
                        var label_view = new ToolSectionLabelView({
                            model: panel_elt
                        });
                        label_view.render(), self.$el.append(label_view.$el);
                    }
                }), self.$el.find("a.tool-link").click(function(e) {
                    var tool_id = $(this).attr("class").split(/\s+/)[0], tool = self.model.get("tools").get(tool_id);
                    self.trigger("tool_link_click", e, tool);
                }), this;
            },
            handle_search_results: function() {
                var results = this.model.get("tool_search").get("results");
                results && 0 === results.length ? $("#search-no-results").show() : $("#search-no-results").hide();
            }
        }), ToolFormView = Backbone.View.extend({
            className: "toolForm",
            render: function() {
                this.$el.children().remove(), this.$el.append(_templates.tool_form(this.model.toJSON()));
            }
        });
        Backbone.View.extend({
            className: "toolMenuAndView",
            initialize: function() {
                this.tool_panel_view = new ToolPanelView({
                    collection: this.collection
                }), this.tool_form_view = new ToolFormView();
            },
            render: function() {
                this.tool_panel_view.render(), this.tool_panel_view.$el.css("float", "left"), this.$el.append(this.tool_panel_view.$el), 
                this.tool_form_view.$el.hide(), this.$el.append(this.tool_form_view.$el);
                var self = this;
                this.tool_panel_view.on("tool_link_click", function(e, tool) {
                    e.preventDefault(), self.show_tool(tool);
                });
            },
            show_tool: function(tool) {
                var self = this;
                tool.fetch().done(function() {
                    self.tool_form_view.model = tool, self.tool_form_view.render(), self.tool_form_view.$el.show(), 
                    $("#left").width("650px");
                });
            }
        });
    }
    return {
        ToolParameter: ToolParameter,
        IntegerToolParameter: IntegerToolParameter,
        SelectToolParameter: SelectToolParameter,
        Tool: Tool,
        ToolCollection: ToolCollection,
        ToolSearch: ToolSearch,
        ToolPanel: ToolPanel,
        ToolPanelView: ToolPanelView,
        ToolFormView: ToolFormView
    };
});