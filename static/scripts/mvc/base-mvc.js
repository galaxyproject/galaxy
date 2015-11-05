define([ "libs/underscore", "libs/backbone", "utils/add-logging", "utils/localization" ], function(_, Backbone, addLogging, _l) {
    function mixin() {
        var args = Array.prototype.slice.call(arguments, 0), lastArg = args.pop();
        return args.unshift(lastArg), _.defaults.apply(_, args);
    }
    function wrapTemplate(template, jsonNamespace) {
        jsonNamespace = jsonNamespace || "model";
        var templateFn = _.template(template.join(""));
        return function(json, view) {
            var templateVars = {
                view: view || {},
                _l: _l
            };
            return templateVars[jsonNamespace] = json || {}, templateFn(templateVars);
        };
    }
    var LoggableMixin = {
        logger: null,
        _logNamespace: "."
    };
    addLogging(LoggableMixin);
    var SessionStorageModel = Backbone.Model.extend({
        initialize: function(initialAttrs) {
            if (this._checkEnabledSessionStorage(), !initialAttrs.id) throw new Error("SessionStorageModel requires an id in the initial attributes");
            this.id = initialAttrs.id;
            var existing = this.isNew() ? {} : this._read(this);
            this.clear({
                silent: !0
            }), this.save(_.extend({}, this.defaults, existing, initialAttrs), {
                silent: !0
            }), this.on("change", function() {
                this.save();
            });
        },
        _checkEnabledSessionStorage: function() {
            try {
                return sessionStorage.length;
            } catch (err) {
                return alert("Please enable cookies in your browser for this Galaxy site"), !1;
            }
        },
        sync: function(method, model, options) {
            options.silent || model.trigger("request", model, {}, options);
            var returned = {};
            switch (method) {
              case "create":
                returned = this._create(model);
                break;

              case "read":
                returned = this._read(model);
                break;

              case "update":
                returned = this._update(model);
                break;

              case "delete":
                returned = this._delete(model);
            }
            return void 0 !== returned || null !== returned ? options.success && options.success() : options.error && options.error(), 
            returned;
        },
        _create: function(model) {
            try {
                var json = model.toJSON(), set = sessionStorage.setItem(model.id, JSON.stringify(json));
                return null === set ? set : json;
            } catch (err) {
                if (!(err instanceof DOMException && navigator.userAgent.indexOf("Safari") > -1)) throw err;
            }
            return null;
        },
        _read: function(model) {
            return JSON.parse(sessionStorage.getItem(model.id));
        },
        _update: function(model) {
            return model._create(model);
        },
        _delete: function(model) {
            return sessionStorage.removeItem(model.id);
        },
        isNew: function() {
            return !sessionStorage.hasOwnProperty(this.id);
        },
        _log: function() {
            return JSON.stringify(this.toJSON(), null, "  ");
        },
        toString: function() {
            return "SessionStorageModel(" + this.id + ")";
        }
    });
    !function() {
        SessionStorageModel.prototype = _.omit(SessionStorageModel.prototype, "url", "urlRoot");
    }();
    var SearchableModelMixin = {
        searchAttributes: [],
        searchAliases: {},
        searchAttribute: function(attrKey, searchFor) {
            var attrVal = this.get(attrKey);
            return searchFor && void 0 !== attrVal && null !== attrVal ? _.isArray(attrVal) ? this._searchArrayAttribute(attrVal, searchFor) : -1 !== attrVal.toString().toLowerCase().indexOf(searchFor.toLowerCase()) : !1;
        },
        _searchArrayAttribute: function(array, searchFor) {
            return searchFor = searchFor.toLowerCase(), _.any(array, function(elem) {
                return -1 !== elem.toString().toLowerCase().indexOf(searchFor.toLowerCase());
            });
        },
        search: function(searchFor) {
            var model = this;
            return _.filter(this.searchAttributes, function(key) {
                return model.searchAttribute(key, searchFor);
            });
        },
        matches: function(term) {
            var ATTR_SPECIFIER = "=", split = term.split(ATTR_SPECIFIER);
            if (split.length >= 2) {
                var attrKey = split[0];
                return attrKey = this.searchAliases[attrKey] || attrKey, this.searchAttribute(attrKey, split[1]);
            }
            return !!this.search(term).length;
        },
        matchesAll: function(terms) {
            var model = this;
            return terms = terms.match(/(".*"|\w*=".*"|\S*)/g).filter(function(s) {
                return !!s;
            }), _.all(terms, function(term) {
                return term = term.replace(/"/g, ""), model.matches(term);
            });
        }
    }, HiddenUntilActivatedViewMixin = {
        hiddenUntilActivated: function($activator, options) {
            if (options = options || {}, this.HUAVOptions = {
                $elementShown: this.$el,
                showFn: jQuery.prototype.toggle,
                showSpeed: "fast"
            }, _.extend(this.HUAVOptions, options || {}), this.HUAVOptions.hasBeenShown = this.HUAVOptions.$elementShown.is(":visible"), 
            this.hidden = this.isHidden(), $activator) {
                var mixin = this;
                $activator.on("click", function() {
                    mixin.toggle(mixin.HUAVOptions.showSpeed);
                });
            }
        },
        isHidden: function() {
            return this.HUAVOptions.$elementShown.is(":hidden");
        },
        toggle: function() {
            return this.hidden ? (this.HUAVOptions.hasBeenShown || _.isFunction(this.HUAVOptions.onshowFirstTime) && (this.HUAVOptions.hasBeenShown = !0, 
            this.HUAVOptions.onshowFirstTime.call(this)), _.isFunction(this.HUAVOptions.onshow) && (this.HUAVOptions.onshow.call(this), 
            this.trigger("hiddenUntilActivated:shown", this)), this.hidden = !1) : (_.isFunction(this.HUAVOptions.onhide) && (this.HUAVOptions.onhide.call(this), 
            this.trigger("hiddenUntilActivated:hidden", this)), this.hidden = !0), this.HUAVOptions.showFn.apply(this.HUAVOptions.$elementShown, arguments);
        }
    }, DraggableViewMixin = {
        initialize: function(attributes) {
            this.draggable = attributes.draggable || !1;
        },
        $dragHandle: function() {
            return this.$(".title-bar");
        },
        toggleDraggable: function() {
            this.draggable ? this.draggableOff() : this.draggableOn();
        },
        draggableOn: function() {
            this.draggable = !0, this.dragStartHandler = _.bind(this._dragStartHandler, this), 
            this.dragEndHandler = _.bind(this._dragEndHandler, this);
            var handle = this.$dragHandle().attr("draggable", !0).get(0);
            handle.addEventListener("dragstart", this.dragStartHandler, !1), handle.addEventListener("dragend", this.dragEndHandler, !1);
        },
        draggableOff: function() {
            this.draggable = !1;
            var handle = this.$dragHandle().attr("draggable", !1).get(0);
            handle.removeEventListener("dragstart", this.dragStartHandler, !1), handle.removeEventListener("dragend", this.dragEndHandler, !1);
        },
        _dragStartHandler: function(event) {
            return event.dataTransfer.effectAllowed = "move", event.dataTransfer.setData("text", JSON.stringify(this.model.toJSON())), 
            this.trigger("draggable:dragstart", event, this), !1;
        },
        _dragEndHandler: function(event) {
            return this.trigger("draggable:dragend", event, this), !1;
        }
    }, SelectableViewMixin = {
        initialize: function(attributes) {
            this.selectable = attributes.selectable || !1, this.selected = attributes.selected || !1;
        },
        $selector: function() {
            return this.$(".selector");
        },
        _renderSelected: function() {
            this.$selector().find("span").toggleClass("fa-check-square-o", this.selected).toggleClass("fa-square-o", !this.selected);
        },
        toggleSelector: function() {
            this.$selector().is(":visible") ? this.hideSelector() : this.showSelector();
        },
        showSelector: function(speed) {
            speed = void 0 !== speed ? speed : this.fxSpeed, this.selectable = !0, this.trigger("selectable", !0, this), 
            this._renderSelected(), this.$selector().show(speed);
        },
        hideSelector: function(speed) {
            speed = void 0 !== speed ? speed : this.fxSpeed, this.selectable = !1, this.trigger("selectable", !1, this), 
            this.$selector().hide(speed);
        },
        toggleSelect: function(event) {
            this.selected ? this.deselect(event) : this.select(event);
        },
        select: function(event) {
            return this.selected || (this.trigger("selected", this, event), this.selected = !0, 
            this._renderSelected()), !1;
        },
        deselect: function(event) {
            return this.selected && (this.trigger("de-selected", this, event), this.selected = !1, 
            this._renderSelected()), !1;
        }
    };
    return {
        LoggableMixin: LoggableMixin,
        SessionStorageModel: SessionStorageModel,
        mixin: mixin,
        SearchableModelMixin: SearchableModelMixin,
        HiddenUntilActivatedViewMixin: HiddenUntilActivatedViewMixin,
        DraggableViewMixin: DraggableViewMixin,
        SelectableViewMixin: SelectableViewMixin,
        wrapTemplate: wrapTemplate
    };
});