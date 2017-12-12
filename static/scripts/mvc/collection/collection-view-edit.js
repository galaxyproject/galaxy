define("mvc/collection/collection-view-edit", ["exports", "mvc/collection/collection-view", "mvc/collection/collection-model", "mvc/collection/collection-li-edit", "mvc/base-mvc", "mvc/tag", "ui/fa-icon-button", "utils/localization", "ui/editable-text"], function(exports, _collectionView, _collectionModel, _collectionLiEdit, _baseMvc, _tag, _faIconButton, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _collectionView2 = _interopRequireDefault(_collectionView);

    var _collectionModel2 = _interopRequireDefault(_collectionModel);

    var _collectionLiEdit2 = _interopRequireDefault(_collectionLiEdit);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _tag2 = _interopRequireDefault(_tag);

    var _faIconButton2 = _interopRequireDefault(_faIconButton);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    /* =============================================================================
    TODO:
    
    ============================================================================= */
    /** @class editable View/Controller for a dataset collection.
     */
    var _super = _collectionView2.default.CollectionView;
    var CollectionViewEdit = _super.extend(
        /** @lends CollectionView.prototype */
        {
            //MODEL is either a DatasetCollection (or subclass) or a DatasetCollectionElement (list of pairs)

            /** logger used to record this.log messages, commonly set to console */
            //logger              : console,

            /** sub view class used for datasets */
            DatasetDCEViewClass: _collectionLiEdit2.default.DatasetDCEListItemEdit,
            /** sub view class used for nested collections */
            NestedDCDCEViewClass: _collectionLiEdit2.default.NestedDCDCEListItemEdit,

            getNestedDCDCEViewClass: function getNestedDCDCEViewClass() {
                return _collectionLiEdit2.default.NestedDCDCEListItemEdit.extend({
                    foldoutPanelClass: CollectionViewEdit
                });
            },

            // ......................................................................... SET UP
            /** Set up the view, set up storage, bind listeners to HistoryContents events
             *  @param {Object} attributes optional settings for the panel
             */
            initialize: function initialize(attributes) {
                _super.prototype.initialize.call(this, attributes);
            },

            /** In this override, make the collection name editable
             */
            _setUpBehaviors: function _setUpBehaviors($where) {
                $where = $where || this.$el;
                _super.prototype._setUpBehaviors.call(this, $where);
                if (!this.model) {
                    return;
                }

                // anon users shouldn't have access to any of the following
                if (!Galaxy.user || Galaxy.user.isAnonymous()) {
                    return;
                }

                this.tagsEditorShown = true;

                //TODO: extract
                var panel = this;

                var nameSelector = "> .controls .name";
                $where.find(nameSelector).attr("title", (0, _localization2.default)("Click to rename collection")).tooltip({
                    placement: "bottom"
                }).make_text_editable({
                    on_finish: function on_finish(newName) {
                        var previousName = panel.model.get("name");
                        if (newName && newName !== previousName) {
                            panel.$el.find(nameSelector).text(newName);
                            panel.model.save({
                                name: newName
                            }).fail(function() {
                                panel.$el.find(nameSelector).text(panel.model.previous("name"));
                            });
                        } else {
                            panel.$el.find(nameSelector).text(previousName);
                        }
                    }
                });
                this.tagsEditor = new _tag2.default.TagsEditor({
                    model: this.model,
                    el: $where.find(".tags-display"),
                    onshowFirstTime: function onshowFirstTime() {
                        this.render();
                    },
                    usePrompt: false
                });
                this.tagsEditor.toggle(true);
            },

            // ........................................................................ misc
            /** string rep */
            toString: function toString() {
                return "CollectionViewEdit(" + (this.model ? this.model.get("name") : "") + ")";
            }
        });

    //==============================================================================
    exports.default = {
        CollectionViewEdit: CollectionViewEdit
    };
});
//# sourceMappingURL=../../../maps/mvc/collection/collection-view-edit.js.map
