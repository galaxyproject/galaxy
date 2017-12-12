define("mvc/collection/pair-collection-creator", ["exports", "mvc/collection/list-collection-creator", "mvc/history/hdca-model", "mvc/base-mvc", "utils/localization"], function(exports, _listCollectionCreator, _hdcaModel, _baseMvc, _localization) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    var _listCollectionCreator2 = _interopRequireDefault(_listCollectionCreator);

    var _hdcaModel2 = _interopRequireDefault(_hdcaModel);

    var _baseMvc2 = _interopRequireDefault(_baseMvc);

    var _localization2 = _interopRequireDefault(_localization);

    function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : {
            default: obj
        };
    }

    var logNamespace = "collections";
    /*==============================================================================
    TODO:
        the paired creator doesn't really mesh with the list creator as parent
            it may be better to make an abstract super class for both
        composites may inherit from this (or vis-versa)
        PairedDatasetCollectionElementView doesn't make a lot of sense
    
    ==============================================================================*/
    /**  */
    var PairedDatasetCollectionElementView = Backbone.View.extend(_baseMvc2.default.LoggableMixin).extend({
        _logNamespace: logNamespace,

        //TODO: use proper class (DatasetDCE or NestedDCDCE (or the union of both))
        tagName: "li",
        className: "collection-element",

        initialize: function initialize(attributes) {
            this.element = attributes.element || {};
            this.identifier = attributes.identifier;
        },

        render: function render() {
            this.$el.attr("data-element-id", this.element.id).html(this.template({
                identifier: this.identifier,
                element: this.element
            }));
            return this;
        },

        //TODO: lots of unused space in the element - possibly load details and display them horiz.
        template: _.template(['<span class="identifier"><%- identifier %></span>', '<span class="name"><%- element.name %></span>'].join("")),

        /** remove the DOM and any listeners */
        destroy: function destroy() {
            this.off();
            this.$el.remove();
        },

        /** string rep */
        toString: function toString() {
            return "DatasetCollectionElementView()";
        }
    });

    // ============================================================================
    var _super = _listCollectionCreator2.default.ListCollectionCreator;

    /** An interface for building collections.
     */
    var PairCollectionCreator = _super.extend({
        /** the class used to display individual elements */
        elementViewClass: PairedDatasetCollectionElementView,
        /** the class this creator will create and save */
        collectionClass: _hdcaModel2.default.HistoryDatasetCollection,
        className: "pair-collection-creator collection-creator flex-row-container",

        /** override to no-op */
        _mangleDuplicateNames: function _mangleDuplicateNames() {},

        // TODO: this whole pattern sucks. There needs to be two classes of problem area:
        //      bad inital choices and
        //      when the user has painted his/her self into a corner during creation/use-of-the-creator
        /** render the entire interface */
        render: function render(speed, callback) {
            if (this.workingElements.length === 2) {
                return _super.prototype.render.call(this, speed, callback);
            }
            return this._renderInvalid(speed, callback);
        },

        // ------------------------------------------------------------------------ rendering elements
        /** render forward/reverse */
        _renderList: function _renderList(speed, callback) {
            //this.debug( '-- _renderList' );
            //precondition: there are two valid elements in workingElements
            var creator = this;

            var $tmp = jQuery("<div/>");
            var $list = creator.$list();

            // lose the original views, create the new, append all at once, then call their renders
            _.each(this.elementViews, function(view) {
                view.destroy();
                creator.removeElementView(view);
            });
            $tmp.append(creator._createForwardElementView().$el);
            $tmp.append(creator._createReverseElementView().$el);
            $list.empty().append($tmp.children());
            _.invoke(creator.elementViews, "render");
        },

        /** create the forward element view */
        _createForwardElementView: function _createForwardElementView() {
            return this._createElementView(this.workingElements[0], {
                identifier: "forward"
            });
        },

        /** create the forward element view */
        _createReverseElementView: function _createReverseElementView() {
            return this._createElementView(this.workingElements[1], {
                identifier: "reverse"
            });
        },

        /** create an element view, cache in elementViews, and return */
        _createElementView: function _createElementView(element, options) {
            var elementView = new this.elementViewClass(_.extend(options, {
                element: element
            }));
            this.elementViews.push(elementView);
            return elementView;
        },

        /** swap the forward, reverse elements and re-render */
        swap: function swap() {
            this.workingElements = [this.workingElements[1], this.workingElements[0]];
            this._renderList();
        },

        events: _.extend(_.clone(_super.prototype.events), {
            "click .swap": "swap"
        }),

        // ------------------------------------------------------------------------ templates
        //TODO: move to require text plugin and load these as text
        //TODO: underscore currently unnecc. bc no vars are used
        //TODO: better way of localizing text-nodes in long strings
        /** underscore template fns attached to class */
        templates: _.extend(_.clone(_super.prototype.templates), {
            /** the middle: element list */
            middle: _.template(['<div class="collection-elements-controls">', '<a class="swap" href="javascript:void(0);" title="', (0, _localization2.default)("Swap forward and reverse datasets"), '">', (0, _localization2.default)("Swap"), "</a>", "</div>", '<div class="collection-elements scroll-container flex-row">', "</div>"].join("")),

            /** help content */
            helpContent: _.template(["<p>", (0, _localization2.default)(["Pair collections are permanent collections containing two datasets: one forward and one reverse. ", "Often these are forward and reverse reads. The pair collections can be passed to tools and ", "workflows in order to have analyses done on both datasets. This interface allows ", "you to create a pair, name it, and swap which is forward and which reverse."].join("")), "</p>", "<ul>", "<li>", (0, _localization2.default)(['Click the <i data-target=".swap">"Swap"</i> link to make your forward dataset the reverse ', "and the reverse dataset forward."].join("")), "</li>", "<li>", (0, _localization2.default)(['Click the <i data-target=".cancel-create">"Cancel"</i> button to exit the interface.'].join("")), "</li>", "</ul><br />", "<p>", (0, _localization2.default)(['Once your collection is complete, enter a <i data-target=".collection-name">name</i> and ', 'click <i data-target=".create-collection">"Create list"</i>.'].join("")), "</p>"].join("")),

            /** a simplified page communicating what went wrong and why the user needs to reselect something else */
            invalidInitial: _.template(['<div class="header flex-row no-flex">', '<div class="alert alert-warning" style="display: block">', '<span class="alert-message">', "<% if( _.size( problems ) ){ %>", (0, _localization2.default)("The following selections could not be included due to problems"), "<ul><% _.each( problems, function( problem ){ %>", "<li><b><%- problem.element.name %></b>: <%- problem.text %></li>", "<% }); %></ul>", "<% } else if( _.size( elements ) === 0 ){ %>", (0, _localization2.default)("No datasets were selected"), ".", "<% } else if( _.size( elements ) === 1 ){ %>", (0, _localization2.default)("Only one dataset was selected"), ": <%- elements[0].name %>", "<% } else if( _.size( elements ) > 2 ){ %>", (0, _localization2.default)("Too many datasets were selected"), ': <%- _.pluck( elements, "name" ).join( ", ") %>', "<% } %>", "<br />", (0, _localization2.default)("Two (and only two) elements are needed for the pair"), ". ", (0, _localization2.default)("You may need to "), '<a class="cancel-create" href="javascript:void(0)">', (0, _localization2.default)("cancel"), "</a> ", (0, _localization2.default)("and reselect new elements"), ".", "</span>", "</div>", "</div>", '<div class="footer flex-row no-flex">', '<div class="actions clear vertically-spaced">', '<div class="other-options pull-left">', '<button class="cancel-create btn" tabindex="-1">', (0, _localization2.default)("Cancel"), "</button>",
                // _l( 'Create a different kind of collection' ),
                "</div>", "</div>", "</div>"
            ].join(""))
        }),

        // ------------------------------------------------------------------------ misc
        /** string rep */
        toString: function toString() {
            return "PairCollectionCreator";
        }
    });

    //==============================================================================
    /** List collection flavor of collectionCreatorModal. */
    var pairCollectionCreatorModal = function _pairCollectionCreatorModal(elements, options) {
        options = options || {};
        options.title = (0, _localization2.default)("Create a collection from a pair of datasets");
        return _listCollectionCreator2.default.collectionCreatorModal(elements, options, PairCollectionCreator);
    };

    //==============================================================================
    /** Use a modal to create a pair collection, then add it to the given history contents.
     *  @returns {Deferred} resolved when the collection is added to the history.
     */
    function createPairCollection(contents, defaultHideSourceItems) {
        var elements = contents.toJSON();

        var promise = pairCollectionCreatorModal(elements, {
            defaultHideSourceItems: defaultHideSourceItems,
            creationFn: function creationFn(elements, name, hideSourceItems) {
                elements = [{
                    name: "forward",
                    src: "hda",
                    id: elements[0].id
                }, {
                    name: "reverse",
                    src: "hda",
                    id: elements[1].id
                }];
                return contents.createHDCA(elements, "paired", name, hideSourceItems);
            }
        });

        return promise;
    }

    //==============================================================================
    exports.default = {
        PairCollectionCreator: PairCollectionCreator,
        pairCollectionCreatorModal: pairCollectionCreatorModal,
        createPairCollection: createPairCollection
    };
});
//# sourceMappingURL=../../../maps/mvc/collection/pair-collection-creator.js.map
