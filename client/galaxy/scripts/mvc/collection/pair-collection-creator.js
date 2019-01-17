import $ from "jquery";
import _ from "underscore";
import Backbone from "backbone";
import LIST_CREATOR from "mvc/collection/list-collection-creator";
import HDCA from "mvc/history/hdca-model";
import BASE_MVC from "mvc/base-mvc";
import _l from "utils/localization";

var logNamespace = "collections";
/*==============================================================================
TODO:
    the paired creator doesn't really mesh with the list creator as parent
        it may be better to make an abstract super class for both
    composites may inherit from this (or vis-versa)
    PairedDatasetCollectionElementView doesn't make a lot of sense

==============================================================================*/
/**  */
var PairedDatasetCollectionElementView = Backbone.View.extend(BASE_MVC.LoggableMixin).extend({
    _logNamespace: logNamespace,

    //TODO: use proper class (DatasetDCE or NestedDCDCE (or the union of both))
    tagName: "li",
    className: "collection-element",

    initialize: function(attributes) {
        this.element = attributes.element || {};
        this.identifier = attributes.identifier;
    },

    render: function() {
        this.$el.attr("data-element-id", this.element.id).html(
            this.template({
                identifier: this.identifier,
                element: this.element
            })
        );
        return this;
    },

    //TODO: lots of unused space in the element - possibly load details and display them horiz.
    template: _.template(
        ['<span class="identifier"><%- identifier %></span>', '<span class="name"><%- element.name %></span>'].join("")
    ),

    /** remove the DOM and any listeners */
    destroy: function() {
        this.off();
        this.$el.remove();
    },

    /** string rep */
    toString: function() {
        return "DatasetCollectionElementView()";
    }
});

// ============================================================================
var _super = LIST_CREATOR.ListCollectionCreator;

/** An interface for building collections.
 */
var PairCollectionCreator = _super.extend({
    /** the class used to display individual elements */
    elementViewClass: PairedDatasetCollectionElementView,
    /** the class this creator will create and save */
    collectionClass: HDCA.HistoryDatasetCollection,
    className: "pair-collection-creator collection-creator flex-row-container",

    /** override to no-op */
    _mangleDuplicateNames: function() {},

    // TODO: this whole pattern sucks. There needs to be two classes of problem area:
    //      bad inital choices and
    //      when the user has painted his/her self into a corner during creation/use-of-the-creator
    /** render the entire interface */
    render: function(speed, callback) {
        if (this.workingElements.length === 2) {
            return _super.prototype.render.call(this, speed, callback);
        }
        return this._renderInvalid(speed, callback);
    },

    // ------------------------------------------------------------------------ rendering elements
    /** render forward/reverse */
    _renderList: function(speed, callback) {
        //this.debug( '-- _renderList' );
        //precondition: there are two valid elements in workingElements
        var creator = this;

        var $tmp = $("<div/>");
        var $list = creator.$list();

        // lose the original views, create the new, append all at once, then call their renders
        _.each(this.elementViews, view => {
            view.destroy();
            creator.removeElementView(view);
        });
        $tmp.append(creator._createForwardElementView().$el);
        $tmp.append(creator._createReverseElementView().$el);
        $list.empty().append($tmp.children());
        _.invoke(creator.elementViews, "render");
    },

    /** create the forward element view */
    _createForwardElementView: function() {
        return this._createElementView(this.workingElements[0], {
            identifier: "forward"
        });
    },

    /** create the forward element view */
    _createReverseElementView: function() {
        return this._createElementView(this.workingElements[1], {
            identifier: "reverse"
        });
    },

    /** create an element view, cache in elementViews, and return */
    _createElementView: function(element, options) {
        var elementView = new this.elementViewClass(
            _.extend(options, {
                element: element
            })
        );
        this.elementViews.push(elementView);
        return elementView;
    },

    /** swap the forward, reverse elements and re-render */
    swap: function() {
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
        middle: _.template(
            [
                '<div class="collection-elements-controls">',
                '<a class="swap" href="javascript:void(0);" title="',
                _l("Swap forward and reverse datasets"),
                '">',
                _l("Swap"),
                "</a>",
                "</div>",
                '<div class="collection-elements scroll-container flex-row">',
                "</div>"
            ].join("")
        ),

        /** help content */
        helpContent: _.template(
            [
                "<p>",
                _l(
                    [
                        "Pair collections are permanent collections containing two datasets: one forward and one reverse. ",
                        "Often these are forward and reverse reads. The pair collections can be passed to tools and ",
                        "workflows in order to have analyses done on both datasets. This interface allows ",
                        "you to create a pair, name it, and swap which is forward and which reverse."
                    ].join("")
                ),
                "</p>",
                "<ul>",
                "<li>",
                _l(
                    [
                        'Click the <i data-target=".swap">"Swap"</i> link to make your forward dataset the reverse ',
                        "and the reverse dataset forward."
                    ].join("")
                ),
                "</li>",
                "<li>",
                _l(['Click the <i data-target=".cancel-create">"Cancel"</i> button to exit the interface.'].join("")),
                "</li>",
                "</ul><br />",
                "<p>",
                _l(
                    [
                        'Once your collection is complete, enter a <i data-target=".collection-name">name</i> and ',
                        'click <i data-target=".create-collection">"Create list"</i>.'
                    ].join("")
                ),
                "</p>"
            ].join("")
        ),

        /** a simplified page communicating what went wrong and why the user needs to reselect something else */
        invalidInitial: _.template(
            [
                '<div class="header flex-row no-flex">',
                '<div class="alert alert-warning" style="display: block">',
                '<span class="alert-message">',
                "<% if( _.size( problems ) ){ %>",
                _l("The following selections could not be included due to problems"),
                "<ul><% _.each( problems, function( problem ){ %>",
                "<li><b><%- problem.element.name %></b>: <%- problem.text %></li>",
                "<% }); %></ul>",
                "<% } else if( _.size( elements ) === 0 ){ %>",
                _l("No datasets were selected"),
                ".",
                "<% } else if( _.size( elements ) === 1 ){ %>",
                _l("Only one dataset was selected"),
                ": <%- elements[0].name %>",
                "<% } else if( _.size( elements ) > 2 ){ %>",
                _l("Too many datasets were selected"),
                ': <%- _.pluck( elements, "name" ).join( ", ") %>',
                "<% } %>",
                "<br />",
                _l("Two (and only two) elements are needed for the pair"),
                ". ",
                _l("You may need to "),
                '<a class="cancel-create" href="javascript:void(0)">',
                _l("cancel"),
                "</a> ",
                _l("and reselect new elements"),
                ".",
                "</span>",
                "</div>",
                "</div>",
                '<div class="footer flex-row no-flex">',
                '<div class="actions clear vertically-spaced">',
                '<div class="other-options float-left">',
                '<button class="cancel-create btn" tabindex="-1">',
                _l("Cancel"),
                "</button>",
                // _l( 'Create a different kind of collection' ),
                "</div>",
                "</div>",
                "</div>"
            ].join("")
        )
    }),

    // ------------------------------------------------------------------------ misc
    /** string rep */
    toString: function() {
        return "PairCollectionCreator";
    }
});

//==============================================================================
/** List collection flavor of collectionCreatorModal. */
var pairCollectionCreatorModal = function _pairCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l("Create a collection from a pair of datasets");
    return LIST_CREATOR.collectionCreatorModal(elements, options, PairCollectionCreator);
};

//==============================================================================
/** Use a modal to create a pair collection, then add it to the given history contents.
 *  @returns {Deferred} resolved when the collection is added to the history.
 */
function createPairCollection(contents, defaultHideSourceItems) {
    var elements = contents.toJSON();
    const copyElements = !defaultHideSourceItems;

    var promise = pairCollectionCreatorModal(elements, {
        defaultHideSourceItems: defaultHideSourceItems,
        creationFn: function(elements, name, hideSourceItems) {
            elements = [
                { name: "forward", src: "hda", id: elements[0].id },
                { name: "reverse", src: "hda", id: elements[1].id }
            ];
            return contents.createHDCA(elements, "paired", name, hideSourceItems, copyElements);
        }
    });

    return promise;
}

//==============================================================================
export default {
    PairCollectionCreator: PairCollectionCreator,
    pairCollectionCreatorModal: pairCollectionCreatorModal,
    createPairCollection: createPairCollection
};
