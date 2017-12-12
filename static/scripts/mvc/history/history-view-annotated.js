define("mvc/history/history-view-annotated", ["exports", "mvc/history/history-view", "mvc/history/hda-li", "mvc/history/hdca-li", "mvc/base-mvc", "utils/localization"], function(exports, _historyView, _hdaLi, _hdcaLi, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _historyView2 = _interopRequireDefault(_historyView);

    var _hdaLi2 = _interopRequireDefault(_hdaLi);

    var _hdcaLi2 = _interopRequireDefault(_hdcaLi);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /* =============================================================================
    TODO:
    
    ============================================================================= */
    var _super = _historyView2.default.HistoryView;
    // used in history/display.mako and history/embed.mako
    /** @class View/Controller for a tabular view of the history model.
     *
     *  As ReadOnlyHistoryView, but with:
     *      history annotation always shown
     *      datasets displayed in a table:
     *          datasets in left cells, dataset annotations in the right
     */
    var AnnotatedHistoryView = _super.extend(
        /** @lends AnnotatedHistoryView.prototype */
        {
            className: _super.prototype.className + " annotated-history-panel",

            // ------------------------------------------------------------------------ panel rendering
            /** In this override, add the history annotation */
            _buildNewRender: function _buildNewRender() {
                //TODO: shouldn't this display regardless (on all non-current panels)?
                var $newRender = _super.prototype._buildNewRender.call(this);
                this.renderHistoryAnnotation($newRender);
                return $newRender;
            },

            /** render the history's annotation as its own field */
            renderHistoryAnnotation: function renderHistoryAnnotation($newRender) {
                var annotation = this.model.get("annotation");
                if (!annotation) {
                    return;
                }
                $newRender.find("> .controls .subtitle").text(annotation);
            },

            /** override to add headers to indicate the dataset, annotation columns */
            renderItems: function renderItems($whereTo) {
                $whereTo = $whereTo || this.$el;
                _super.prototype.renderItems.call(this, $whereTo);

                var $controls = $whereTo.find("> .controls");
                $controls.find(".contents-container.headers").remove();

                var $headers = $('<div class="contents-container headers"/>').append([$('<div class="history-content header"/>').text((0, _localization2.default)("Dataset")), $('<div class="additional-info header"/>').text((0, _localization2.default)("Annotation"))]).appendTo($controls);

                return self.views;
            },

            // ------------------------------------------------------------------------ sub-views
            /** override to wrap each subview */
            _renderItemView$el: function _renderItemView$el(view) {
                return $('<div class="contents-container"/>').append([view.render(0).$el, $('<div class="additional-info"/>').text(view.model.get("annotation") || "")]);
            },

            // ------------------------------------------------------------------------ panel events
            events: _.extend(_.clone(_super.prototype.events), {
                // clicking on any part of the row will expand the items
                "click .contents-container": function clickContentsContainer(ev) {
                    ev.stopPropagation();
                    $(ev.currentTarget).find(".list-item .title-bar").click();
                },
                // prevent propagation on icon btns so they won't bubble up to tr and toggleBodyVisibility
                "click .icon-btn": function clickIconBtn(ev) {
                    ev.stopPropagation();
                    // stopProp will prevent bootstrap from getting the click needed to open a dropdown
                    //  in the case of metafile download buttons - workaround here
                    var $currTarget = $(ev.currentTarget);
                    if ($currTarget.length && $currTarget.attr("data-toggle") === "dropdown") {
                        $currTarget.dropdown("toggle");
                    }
                }
            }),

            _clickSectionLink: function _clickSectionLink(ev) {
                var sectionNumber = $(ev.currentTarget).parent().parent().data("section");
                this.openSection(sectionNumber);
            },

            // ........................................................................ misc
            /** Return a string rep of the history */
            toString: function toString() {
                return "AnnotatedHistoryView(" + (this.model ? this.model.get("name") : "") + ")";
            }
        });

    //==============================================================================
    exports.default = {
        AnnotatedHistoryView: AnnotatedHistoryView
    };
});
//# sourceMappingURL=../../../maps/mvc/history/history-view-annotated.js.map
