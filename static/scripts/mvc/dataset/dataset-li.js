define("mvc/dataset/dataset-li", ["exports", "mvc/list/list-item", "mvc/dataset/states", "ui/fa-icon-button", "mvc/base-mvc", "utils/localization"], function(exports, _listItem, _states, _faIconButton, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _listItem2 = _interopRequireDefault(_listItem);

    var _states2 = _interopRequireDefault(_states);

    var _faIconButton2 = _interopRequireDefault(_faIconButton);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "dataset";
    /*==============================================================================
    TODO:
        straighten out state rendering and templates used
        inaccessible/STATES.NOT_VIEWABLE is a special case
        simplify button rendering
    
    ==============================================================================*/
    var _super = _listItem2.default.ListItemView;
    /** @class Read only list view for either LDDAs, HDAs, or HDADCEs.
     *      Roughly, any DatasetInstance (and not a raw Dataset).
     */
    var DatasetListItemView = _super.extend(
        /** @lends DatasetListItemView.prototype */
        {
            _logNamespace: logNamespace,

            className: _super.prototype.className + " dataset",
            //TODO:?? doesn't exactly match an hda's type_id
            id: function id() {
                return ["dataset", this.model.get("id")].join("-");
            },

            /** Set up: instance vars, options, and event handlers */
            initialize: function initialize(attributes) {
                if (attributes.logger) {
                    this.logger = this.model.logger = attributes.logger;
                }
                this.log(this + ".initialize:", attributes);
                _super.prototype.initialize.call(this, attributes);

                /** where should pages from links be displayed? (default to new tab/window) */
                this.linkTarget = attributes.linkTarget || "_blank";
            },

            /** event listeners */
            _setUpListeners: function _setUpListeners() {
                _super.prototype._setUpListeners.call(this);
                var self = this;

                // re-rendering on any model changes
                return self.listenTo(self.model, {
                    change: function change(model) {
                        // if the model moved into the ready state and is expanded without details, fetch those details now
                        if (self.model.changedAttributes().state && self.model.inReadyState() && self.expanded && !self.model.hasDetails()) {
                            // normally, will render automatically (due to fetch -> change),
                            // but! setting_metadata sometimes doesn't cause any other changes besides state
                            // so, not rendering causes it to seem frozen in setting_metadata state
                            self.model.fetch({
                                silent: true
                            }).done(function() {
                                self.render();
                            });
                        } else {
                            if (_.has(model.changed, "tags") && _.keys(model.changed).length === 1) {
                                // If only the tags have changed, rerender specifically
                                // the titlebar region.  Otherwise default to the full
                                // render.
                                self.$(".nametags").html(self._renderNametags());
                            } else {
                                self.render();
                            }
                        }
                    }
                });
            },

            // ......................................................................... expandable
            /** In this override, only get details if in the ready state, get rerunnable if in other states.
             *  Note: fetch with no 'change' event triggering to prevent automatic rendering.
             */
            _fetchModelDetails: function _fetchModelDetails() {
                var view = this;
                if (view.model.inReadyState() && !view.model.hasDetails()) {
                    return view.model.fetch({
                        silent: true
                    });
                }
                return jQuery.when();
            },

            // ......................................................................... removal
            /** Remove this view's html from the DOM and remove all event listeners.
             *  @param {Number or String} speed jq effect speed
             *  @param {Function} callback      an optional function called when removal is done (scoped to this view)
             */
            remove: function remove(speed, callback) {
                var view = this;
                speed = speed || this.fxSpeed;
                this.$el.fadeOut(speed, function() {
                    Backbone.View.prototype.remove.call(view);
                    if (callback) {
                        callback.call(view);
                    }
                });
            },

            // ......................................................................... rendering
            /* TODO:
            dataset states are the issue primarily making dataset rendering complex
                each state should have it's own way of displaying/set of details
                often with different actions that can be applied
            throw in deleted/purged/visible and things get complicated easily
            I've considered (a couple of times) - creating a view for each state
                - but recreating the view during an update...seems wrong
            */
            /** In this override, add the dataset state as a class for use with state-based CSS */
            _swapNewRender: function _swapNewRender($newRender) {
                _super.prototype._swapNewRender.call(this, $newRender);
                if (this.model.has("state")) {
                    this.$el.addClass("state-" + this.model.get("state"));
                }
                return this.$el;
            },

            // ................................................................................ titlebar
            /** In this override, add the dataset display button. */
            _renderPrimaryActions: function _renderPrimaryActions() {
                // render just the display for read-only
                return [this._renderDisplayButton()];
            },

            /** Render icon-button to display dataset data */
            _renderDisplayButton: function _renderDisplayButton() {
                // don't show display if not viewable or not accessible
                var state = this.model.get("state");
                if (state === _states2.default.NOT_VIEWABLE || state === _states2.default.DISCARDED || !this.model.get("accessible")) {
                    return null;
                }

                var displayBtnData = {
                    target: this.linkTarget,
                    classes: "display-btn"
                };

                // show a disabled display if the data's been purged
                if (this.model.get("purged")) {
                    displayBtnData.disabled = true;
                    displayBtnData.title = (0, _localization2.default)("Cannot display datasets removed from disk");

                    // disable if still uploading
                } else if (state === _states2.default.UPLOAD) {
                    displayBtnData.disabled = true;
                    displayBtnData.title = (0, _localization2.default)("This dataset must finish uploading before it can be viewed");

                    // disable if still new
                } else if (state === _states2.default.NEW) {
                    displayBtnData.disabled = true;
                    displayBtnData.title = (0, _localization2.default)("This dataset is not yet viewable");
                } else {
                    displayBtnData.title = (0, _localization2.default)("View data");

                    // default link for dataset
                    displayBtnData.href = this.model.urls.display;

                    // add frame manager option onclick event
                    var self = this;
                    displayBtnData.onclick = function(ev) {
                        if (Galaxy.frame && Galaxy.frame.active) {
                            // Add dataset to frames.
                            Galaxy.frame.addDataset(self.model.get("id"));
                            ev.preventDefault();
                        }
                    };
                }
                displayBtnData.faIcon = "fa-eye";
                return (0, _faIconButton2.default)(displayBtnData);
            },

            // ......................................................................... rendering details
            /** Render the enclosing div of the hda body and, if expanded, the html in the body
             *  @returns {jQuery} rendered DOM
             */
            _renderDetails: function _renderDetails() {
                //TODO: generalize to be allow different details for each state

                // no access - render nothing but a message
                if (this.model.get("state") === _states2.default.NOT_VIEWABLE) {
                    return $(this.templates.noAccess(this.model.toJSON(), this));
                }

                var $details = _super.prototype._renderDetails.call(this);
                $details.find(".actions .left").empty().append(this._renderSecondaryActions());
                $details.find(".summary").html(this._renderSummary()).prepend(this._renderDetailMessages());
                $details.find(".display-applications").html(this._renderDisplayApplications());

                this._setUpBehaviors($details);
                return $details;
            },

            /** Defer to the appropo summary rendering fn based on state */
            _renderSummary: function _renderSummary() {
                var json = this.model.toJSON();
                var summaryRenderFn = this.templates.summaries[json.state];
                summaryRenderFn = summaryRenderFn || this.templates.summaries.unknown;
                return summaryRenderFn(json, this);
            },

            /** Render messages to be displayed only when the details are shown */
            _renderDetailMessages: function _renderDetailMessages() {
                var view = this;
                var $warnings = $('<div class="detail-messages"></div>');
                var json = view.model.toJSON();
                //TODO:! unordered (map)
                _.each(view.templates.detailMessages, function(templateFn) {
                    $warnings.append($(templateFn(json, view)));
                });
                return $warnings;
            },

            /** Render the external display application links */
            _renderDisplayApplications: function _renderDisplayApplications() {
                if (this.model.isDeletedOrPurged()) {
                    return "";
                }
                // render both old and new display apps using the same template
                return [this.templates.displayApplications(this.model.get("display_apps"), this), this.templates.displayApplications(this.model.get("display_types"), this)].join("");
            },

            // ......................................................................... secondary/details actions
            /** A series of links/buttons for less commonly used actions: re-run, info, etc. */
            _renderSecondaryActions: function _renderSecondaryActions() {
                this.debug("_renderSecondaryActions");
                switch (this.model.get("state")) {
                    case _states2.default.NOT_VIEWABLE:
                        return [];
                    case _states2.default.OK:
                    case _states2.default.FAILED_METADATA:
                    case _states2.default.ERROR:
                        return [this._renderDownloadButton(), this._renderShowParamsButton()];
                }
                return [this._renderShowParamsButton()];
            },

            /** Render icon-button to show the input and output (stdout/err) for the job that created this.
             *  @returns {jQuery} rendered DOM
             */
            _renderShowParamsButton: function _renderShowParamsButton() {
                // gen. safe to show in all cases
                return (0, _faIconButton2.default)({
                    title: (0, _localization2.default)("View details"),
                    classes: "params-btn",
                    href: this.model.urls.show_params,
                    target: this.linkTarget,
                    faIcon: "fa-info-circle",
                    onclick: function onclick(ev) {
                        if (Galaxy.frame && Galaxy.frame.active) {
                            Galaxy.frame.add({
                                title: (0, _localization2.default)("Dataset details"),
                                url: this.href
                            });
                            ev.preventDefault();
                            ev.stopPropagation();
                        }
                    }
                });
            },

            /** Render icon-button/popupmenu to download the data (and/or the associated meta files (bai, etc.)) for this.
             *  @returns {jQuery} rendered DOM
             */
            _renderDownloadButton: function _renderDownloadButton() {
                // don't show anything if the data's been purged
                if (this.model.get("purged") || !this.model.hasData()) {
                    return null;
                }

                // return either: a popupmenu with links to download assoc. meta files (if there are meta files)
                //  or a single download icon-button (if there are no meta files)
                if (!_.isEmpty(this.model.get("meta_files"))) {
                    return this._renderMetaFileDownloadButton();
                }

                return $(['<a class="download-btn icon-btn" ', 'href="', this.model.urls.download, "\" title=\"" + (0, _localization2.default)("Download") + "\" download>", '<span class="fa fa-floppy-o"></span>', "</a>"].join(""));
            },

            /** Render the download button which opens a dropdown with links to download assoc. meta files (indeces, etc.) */
            _renderMetaFileDownloadButton: function _renderMetaFileDownloadButton() {
                var urls = this.model.urls;
                return $(['<div class="metafile-dropdown dropdown">', '<a class="download-btn icon-btn" href="javascript:void(0)" data-toggle="dropdown"', " title=\"" + (0, _localization2.default)("Download") + "\">", '<span class="fa fa-floppy-o"></span>', "</a>", '<ul class="dropdown-menu" role="menu" aria-labelledby="dLabel">', "<li><a href=\"" + urls.download + "\" download>", (0, _localization2.default)("Download dataset"), "</a></li>", _.map(this.model.get("meta_files"), function(meta_file) {
                    return ['<li><a href="', urls.meta_download + meta_file.file_type, '">', (0, _localization2.default)("Download"), " ", meta_file.file_type, "</a></li>"].join("");
                }).join("\n"), "</ul>", "</div>"].join("\n"));
            },

            _renderNametags: function _renderNametags() {
                var tpl = _.template(["<% _.each(_.sortBy(_.uniq(tags), function(x) { return x }), function(tag){ %>", '<% if (tag.indexOf("name:") == 0){ %>', '<span class="label label-info"><%- tag.slice(5) %></span>', "<% } %>", "<% }); %>"].join(""));
                return tpl({
                    tags: this.model.get("tags")
                });
            },

            // ......................................................................... misc
            events: _.extend(_.clone(_super.prototype.events), {
                "click .display-btn": function clickDisplayBtn(ev) {
                    this.trigger("display", this, ev);
                },
                "click .params-btn": function clickParamsBtn(ev) {
                    this.trigger("params", this, ev);
                },
                "click .download-btn": function clickDownloadBtn(ev) {
                    this.trigger("download", this, ev);
                }
            }),

            // ......................................................................... misc
            /** String representation */
            toString: function toString() {
                var modelString = this.model ? "" + this.model : "(no model)";
                return "DatasetListItemView(" + modelString + ")";
            }
        });

    // ............................................................................ TEMPLATES
    /** underscore templates */
    DatasetListItemView.prototype.templates = function() {
        //TODO: move to require text! plugin

        var warnings = _.extend({}, _super.prototype.templates.warnings, {
            failed_metadata: _baseMvc2.default.wrapTemplate([
                // failed metadata is rendered as a warning on an otherwise ok dataset view
                '<% if( model.state === "failed_metadata" ){ %>', '<div class="warningmessagesmall">', (0, _localization2.default)("An error occurred setting the metadata for this dataset"), "</div>", "<% } %>"
            ]),
            error: _baseMvc2.default.wrapTemplate([
                // error during index fetch - show error on dataset
                "<% if( model.error ){ %>", '<div class="errormessagesmall">', (0, _localization2.default)("There was an error getting the data for this dataset"), ": <%- model.error %>", "</div>", "<% } %>"
            ]),
            purged: _baseMvc2.default.wrapTemplate(["<% if( model.purged ){ %>", '<div class="purged-msg warningmessagesmall">', (0, _localization2.default)("This dataset has been deleted and removed from disk"), "</div>", "<% } %>"]),
            deleted: _baseMvc2.default.wrapTemplate([
                // deleted not purged
                "<% if( model.deleted && !model.purged ){ %>", '<div class="deleted-msg warningmessagesmall">', (0, _localization2.default)("This dataset has been deleted"), "</div>", "<% } %>"
            ])

            //NOTE: hidden warning is only needed for HDAs
        });

        var detailsTemplate = _baseMvc2.default.wrapTemplate(['<div class="details">', '<div class="summary"></div>', '<div class="actions clear">', '<div class="left"></div>', '<div class="right"></div>', "</div>",

            // do not display tags, annotation, display apps, or peek when deleted
            "<% if( !dataset.deleted && !dataset.purged ){ %>", '<div class="tags-display"></div>', '<div class="annotation-display"></div>', '<div class="display-applications"></div>', "<% if( dataset.peek ){ %>", '<pre class="dataset-peek"><%= dataset.peek %></pre>', "<% } %>", "<% } %>", "</div>"
        ], "dataset");

        var noAccessTemplate = _baseMvc2.default.wrapTemplate(['<div class="details">', '<div class="summary">', (0, _localization2.default)("You do not have permission to view this dataset"), "</div>", "</div>"], "dataset");

        //TODO: still toooooooooooooo complex - rework
        var summaryTemplates = {};
        summaryTemplates[_states2.default.OK] = summaryTemplates[_states2.default.FAILED_METADATA] = _baseMvc2.default.wrapTemplate(["<% if( dataset.misc_blurb ){ %>", '<div class="blurb">', '<span class="value"><%- dataset.misc_blurb %></span>', "</div>", "<% } %>", "<% if( dataset.file_ext ){ %>", '<div class="datatype">', '<label class="prompt">', (0, _localization2.default)("format"), "</label>", '<span class="value"><%- dataset.file_ext %></span>', "</div>", "<% } %>", "<% if( dataset.metadata_dbkey ){ %>", '<div class="dbkey">', '<label class="prompt">', (0, _localization2.default)("database"), "</label>", '<span class="value">', "<%- dataset.metadata_dbkey %>", "</span>", "</div>", "<% } %>", "<% if( dataset.misc_info ){ %>", '<div class="info">', '<span class="value"><%- dataset.misc_info %></span>', "</div>", "<% } %>"], "dataset");
        summaryTemplates[_states2.default.NEW] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("This is a new dataset and not all of its data are available yet"), "</div>"], "dataset");
        summaryTemplates[_states2.default.NOT_VIEWABLE] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("You do not have permission to view this dataset"), "</div>"], "dataset");
        summaryTemplates[_states2.default.DISCARDED] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("The job creating this dataset was cancelled before completion"), "</div>"], "dataset");
        summaryTemplates[_states2.default.QUEUED] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("This job is waiting to run"), "</div>"], "dataset");
        summaryTemplates[_states2.default.RUNNING] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("This job is currently running"), "</div>"], "dataset");
        summaryTemplates[_states2.default.UPLOAD] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("This dataset is currently uploading"), "</div>"], "dataset");
        summaryTemplates[_states2.default.SETTING_METADATA] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("Metadata is being auto-detected"), "</div>"], "dataset");
        summaryTemplates[_states2.default.PAUSED] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)('This job is paused. Use the "Resume Paused Jobs" in the history menu to resume'), "</div>"], "dataset");
        summaryTemplates[_states2.default.ERROR] = _baseMvc2.default.wrapTemplate(["<% if( !dataset.purged ){ %>", "<div><%- dataset.misc_blurb %></div>", "<% } %>", '<span class="help-text">', (0, _localization2.default)("An error occurred with this dataset"), ":</span>", '<div class="job-error-text"><%- dataset.misc_info %></div>'], "dataset");
        summaryTemplates[_states2.default.EMPTY] = _baseMvc2.default.wrapTemplate(["<div>", (0, _localization2.default)("No data"), ": <i><%- dataset.misc_blurb %></i></div>"], "dataset");
        summaryTemplates.unknown = _baseMvc2.default.wrapTemplate(['<div>Error: unknown dataset state: "<%- dataset.state %>"</div>'], "dataset");

        // messages to be displayed only within the details section ('below the fold')
        var detailMessageTemplates = {
            resubmitted: _baseMvc2.default.wrapTemplate([
                // deleted not purged
                "<% if( model.resubmitted ){ %>", '<div class="resubmitted-msg infomessagesmall">', (0, _localization2.default)("The job creating this dataset has been resubmitted"), "</div>", "<% } %>"
            ])
        };

        // this is applied to both old and new style display apps
        var displayApplicationsTemplate = _baseMvc2.default.wrapTemplate(["<% _.each( apps, function( app ){ %>", '<div class="display-application">', '<span class="display-application-location"><%- app.label %></span> ', '<span class="display-application-links">', "<% _.each( app.links, function( link ){ %>", '<a target="<%- link.target %>" href="<%- link.href %>">', "<% print( _l( link.text ) ); %>", "</a> ", "<% }); %>", "</span>", "</div>", "<% }); %>"], "apps");

        return _.extend({}, _super.prototype.templates, {
            warnings: warnings,
            details: detailsTemplate,
            noAccess: noAccessTemplate,
            summaries: summaryTemplates,
            detailMessages: detailMessageTemplates,
            displayApplications: displayApplicationsTemplate
        });
    }();

    // ============================================================================
    exports.default = {
        DatasetListItemView: DatasetListItemView
    };
});
//# sourceMappingURL=../../../maps/mvc/dataset/dataset-li.js.map
