<template>
    <collection-creator>
        <template v-slot: help-content>
            <p>
                {{
                    _l(
                        [
                            "Collections of datasets are permanent, ordered lists of datasets that can be passed to tools ",
                            "and workflows in order to have analyses done on each member of the entire group. This interface allows ",
                            "you to create a collection and re-order the final collection.",
                        ].join("")
                    )
                }}
            </p>
            <ul>
                <li>
                    _l("Rename elements in the list by clicking on
                    <i data-target=".collection-element .name">the existing name</i>.")
                </li>
                <li>
                    _l("Discard elements from the final created list by clicking on the
                    <i data-target=".collection-element .discard">"Discard"</i> button.")
                </li>
                <li>
                    _l("Reorder the list by clicking and dragging elements. Select multiple elements by clicking on
                    <i data-target=".collection-element">them</i> and you can then move those selected by dragging the
                    entire group. Deselect them by clicking them again or by clicking the the
                    <i data-target=".clear-selected">"Clear selected"</i> link.")
                </li>
                <li>
                    _l("Click the <i data-target=".reset">"Start over"</i> link to begin again as if you had just opened
                    the interface.)
                </li>
                <li>_l("Click the <i data-target=".cancel-create">"Cancel"</i> button to exit the interface.")</li>
            </ul>
            <br />
            <p>
                _l("Once your collection is complete, enter a <i data-target=".collection-name">name</i> and click
                <i data-target=".create-collection">"Create list"</i>.")
            </p>
            <a class="less-help" href="javascript:void(0);" role="button"> _l("Less")_ </a
            ><span class="alert-message"></span>
        </template>
        <template v-slot:middle-content>
            <div class="collection-elements-controls">
                <a class="reset" href="javascript:void(0);" role="button" title="titleUndoButton">
                    _l("Start over")
                </a>
                <a class="clear-selected" href="javascript:void(0);" role="button" title="titleDeselectButton">
                    _l("Clear selected")
                </a>
            </div>
            <div class="collection-elements scroll-container flex-row"></div>
        </template>
    </collection-creator>
    <!-- <div>
          <v-on:click.more-help="_clickMoreHelp"/>
          <v-on:click.less-help="_clickLessHelp">
          <v-on:click.main-help="_toggleHelp"/>
          <v-on:click.header.alert button="_hideAlert"/>
          <v-on:click.collection-elements="clearSelectedElements"/>
          <v-on:click.reset="reset"/>
          <v-on:click.clear-selected="clearSelectedElements"/>
          <v-on:click.cancel-create="_cancelCreate"/>
          <v-on:click.create-collection="_clickCreate"/>
          <v-on:dragover.collection-elements="_dravoverElements"/>
          <v-on:drop.collection-elements="_dropElements"/>
          <v-on:collection-element.dragstart .collection-elements="_elementDragstart"/>
          <v-on:collection-element.dragend . collection-elements="_elementDragend"/>
          <v-on:change.collection-name="_changeName"/>
          <v-on:keydown.collection-name="_nameCheckForEnter"/>
          <v-on:change.hide-originals="_changeHideOriginals"/>
        </div>
    </div> -->
</template>

<script>
import HDCA from "mvc/history/hdca-model";
import CollectionCreatorMixin from "mvc/collection/mixins/CollectionCreatorMixin";
import DatasetCollectionElementView from "mvc/collection/DatasetCollectionElementView";
import _ from "underscore";
import $ from "jquery";
import _l from "utils/localization";
import STATES from "mvc/dataset/states";
import "ui/hoverhighlight";



export default {
    data: function () {
        return {
            minElements: 1,
            elementViewClass: DatasetCollectionElementView,
            collectionClass: HDCA.HistoryDatasetCollection,
            className: "list-collection-creator collection-creator flex-row-container",
            footerSettings: {
                ".hide-originals": "hideOriginals",
            },
            titleMoreHelp: _l("Close and show more help"),
            titleUndoButton: _l("Undo all reordering and discards"),
            titleDeselectButton: _l("De-select all selected datasets"),
            placeholderEnterName: _l("Enter a name for your new collection"),
        }
    },
    mixins: [ CollectionCreatorMixin ],
    props: {
        creationFn: {
            type: Function,
            required: true,
        },
        /** fn to call when the collection is created (scoped to this) */
        oncreate: {
            type: Function,
            required: false,
            default: () => {},
        },
        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        oncancel: {
            type: Function,
            required: false,
            default: () => {},
        },
        /** distance from list edge to begin autoscrolling list */
        autoscrollDist: {
            type: Number,
            required: false,
            default: 24,
        },
        /** Color passed to hoverhighlight */
        highlightClr: {
            type: String,
            required: false,
            default: "rgba( 64, 255, 255, 1.0 )",
        },
    },
    computed: {},
    methods: {
        /** set up instance vars */
        _instanceSetUp: function () {
            /** Ids of elements that have been selected by the user - to preserve over renders */
            this.selectedIds = {};
            /** DOM elements currently being dragged */
            this.$dragging = null;
            /** Used for blocking UI events during ajax/operations (don't post twice) */
            this.blocking = false;
        },

        // ------------------------------------------------------------------------ process raw list
        /** set up main data */
        _elementsSetUp: function () {
            //this.debug( '-- _dataSetUp' );
            /** a list of invalid elements and the reasons they aren't valid */
            this.invalidElements = [];
            //TODO: handle fundamental problem of syncing DOM, views, and list here
            /** data for list in progress */
            this.workingElements = [];
            /** views for workingElements */
            this.elementViews = [];

            // copy initial list, sort, add ids if needed
            this.workingElements = this.initialElements.slice(0);
            this._ensureElementIds();
            this._validateElements();
            this._mangleDuplicateNames();
            this._sortElements();
        },
        /** separate working list into valid and invalid elements for this collection */
        _validateElements: function () {
            var creator = this;
            creator.invalidElements = [];

            this.workingElements = this.workingElements.filter((element) => {
                var problem = creator._isElementInvalid(element);
                if (problem) {
                    creator.invalidElements.push({
                        element: element,
                        text: problem,
                    });
                }
                return !problem;
            });
            return this.workingElements;
        },
        /** add ids to dataset objs in initial list if none */
        _ensureElementIds: function () {
            this.workingElements.forEach((element) => {
                if (!Object.prototype.hasOwnProperty.call(element, "id")) {
                    element.id = _.uniqueId();
                }
            });
            return this.workingElements;
        },

        /** describe what is wrong with a particular element if anything */
        _isElementInvalid: function (element) {
            if (element.history_content_type === "dataset_collection") {
                return _l("is a collection, this is not allowed");
            }
            var validState = element.state === STATES.OK || _.contains(STATES.NOT_READY_STATES, element.state);
            if (!validState) {
                return _l("has errored, is paused, or is not accessible");
            }
            if (element.deleted || element.purged) {
                return _l("has been deleted or purged");
            }
            return null;
        },

        /** mangle duplicate names using a mac-like '(counter)' addition to any duplicates */
        _mangleDuplicateNames: function () {
            var SAFETY = 900;
            var counter = 1;
            var existingNames = {};
            this.workingElements.forEach((element) => {
                var currName = element.name;
                while (Object.prototype.hasOwnProperty.call(existingNames, currName)) {
                    currName = `${element.name} (${counter})`;
                    counter += 1;
                    if (counter >= SAFETY) {
                        throw new Error("Safety hit in while loop - thats impressive");
                    }
                }
                element.name = currName;
                existingNames[element.name] = true;
            });
        },

        /** sort a list of elements */
        _sortElements: function (list) {
            // // currently only natural sort by name
            // this.workingElements.sort( function( a, b ){ return naturalSort( a.name, b.name ); });
            // return this.workingElements;
        },

        // ------------------------------------------------------------------------ rendering
        // templates : ListCollectionCreator.templates,
        /** render the entire interface */
        render: function (speed, callback) {
            //this.debug( '-- _render' );
            if (this.workingElements.length < this.minElements) {
                return this._renderInvalid(speed, callback);
            }

            this.$el.empty().html(this.templates.main());
            this._renderHeader(speed);
            this._renderMiddle(speed);
            this._renderFooter(speed);
            this._addPluginComponents();
            this.$(".collection-name").focus();
            this.trigger("rendered", this);
            return this;
        },

        /** render a simplified interface aimed at telling the user why they can't move forward */
        _renderInvalid: function (speed, callback) {
            //this.debug( '-- _render' );
            this.$el.empty().html(
                this.templates.invalidInitial({
                    problems: this.invalidElements,
                    elements: this.workingElements,
                })
            );
            if (typeof this.oncancel === "function") {
                this.$(".cancel-create.btn").show();
            }
            this.trigger("rendered", this);
            return this;
        },

        /** render the header section */
        _renderHeader: function (speed, callback) {
            var $header = this.$(".header")
                .empty()
                .html(this.templates.header())
                .find(".help-content")
                .prepend($(this.templates.helpContent()));
            //TODO: should only show once despite calling _renderHeader again
            if (this.invalidElements.length) {
                this._invalidElementsAlert();
            }
            return $header;
        },

        /** render the middle including the elements */
        _renderMiddle: function (speed, callback) {
            var $middle = this.$(".middle").empty().html(this.templates.middle());
            this._renderList(speed);
            return $middle;
        },

        /** add any jQuery/bootstrap/custom plugins to elements rendered */
        _addPluginComponents: function () {
            this.$(".help-content i").hoverhighlight(".collection-creator", this.highlightClr);
        },

        /** build and show an alert describing any elements that could not be included due to problems */
        _invalidElementsAlert: function () {
            this._showAlert(
                this.templates.invalidElements({
                    problems: this.invalidElements,
                }),
                "alert-warning"
            );
        },

        _disableNameAndCreate: function (disable) {
            disable = !_.isUndefined(disable) ? disable : true;
            if (disable) {
                this.$(".collection-name").prop("disabled", true);
                this.$(".create-collection").toggleClass("disabled", true);
                // } else {
                //     this.$( '.collection-name' ).prop( 'disabled', false );
                //     this.$( '.create-collection' ).removeClass( 'disable' );
            }
        },

        // ------------------------------------------------------------------------ rendering elements
        /** conv. to the main list display DOM */
        $list: function () {
            return this.$(".collection-elements");
        },

        /** show or hide the clear selected control based on the num of selected elements */
        _renderClearSelected: function () {
            if (_.size(this.selectedIds)) {
                this.$(".collection-elements-controls > .clear-selected").show();
            } else {
                this.$(".collection-elements-controls > .clear-selected").hide();
            }
        },

        /** render the elements in order (or a warning if no elements found) */
        _renderList: function (speed, callback) {
            //this.debug( '-- _renderList' );
            var creator = this;

            var $tmp = $("<div/>");
            var $list = creator.$list();

            _.each(this.elementViews, (view) => {
                view.destroy();
                creator.removeElementView(view);
            });

            // if( !this.workingElements.length ){
            //     this._renderNoValidElements();
            //     return;
            // }

            creator.workingElements.forEach((element) => {
                var elementView = creator._createElementView(element);
                $tmp.append(elementView.$el);
            });

            creator._renderClearSelected();
            $list.empty().append($tmp.children());
            _.invoke(creator.elementViews, "render");

            if ($list.height() > $list.css("max-height")) {
                $list.css("border-width", "1px 0px 1px 0px");
            } else {
                $list.css("border-width", "0px");
            }
        },

        /** create an element view, cache in elementViews, set up listeners, and return */
        _createElementView: function (element) {
            var elementView = new this.elementViewClass({
                //TODO: use non-generic class or not all
                // model : COLLECTION.DatasetDCE( element )
                element: element,
                selected: _.has(this.selectedIds, element.id),
            });
            this.elementViews.push(elementView);
            this._listenToElementView(elementView);
            return elementView;
        },

        /** listen to any element events */
        _listenToElementView: function (view) {
            var creator = this;
            creator.listenTo(view, {
                select: function (data) {
                    var element = data.source.element;
                    if (data.selected) {
                        creator.selectedIds[element.id] = true;
                    } else {
                        delete creator.selectedIds[element.id];
                    }
                    creator.trigger("elements:select", data);
                },
                discard: function (data) {
                    creator.trigger("elements:discard", data);
                },
            });
        },
        /** add a new element view based on the json in element */
        addElementView: function (element) {
            //TODO: workingElements is sorted, add element in appropo index
            // add element, sort elements, find element index
            // var view = this._createElementView( element );
            // return view;
        },

        /** stop listening to view and remove from caches */
        removeElementView: function (view) {
            delete this.selectedIds[view.element.id];
            this._renderClearSelected();

            this.elementViews = _.without(this.elementViews, view);
            this.stopListening(view);
        },

        /** render a message in the list that no elements remain to create a collection */
        _renderNoElementsLeft: function () {
            this._disableNameAndCreate(true);
            this.$(".collection-elements").append(this.templates.noElementsLeft());
        },

        // /** render a message in the list that no valid elements were found to create a collection */
        // _renderNoValidElements : function(){
        //     this._disableNameAndCreate( true );
        //     this.$( '.collection-elements' ).append( this.templates.noValidElements() );
        // },

        // ------------------------------------------------------------------------ API
        /** convert element into JSON compatible with the collections API */
        _elementToJSON: function (element) {
            // return element.toJSON();
            return element;
        },

        /** create the collection via the API
         *  @returns {jQuery.xhr Object} the jquery ajax request
         */
        createList: function (name) {
            if (!this.workingElements.length) {
                var message = `${_l("No valid elements for final list")}. `;
                message += `<a class="cancel-create" href="javascript:void(0);" role="button">${_l("Cancel")}</a> `;
                message += _l("or");
                message += ` <a class="reset" href="javascript:void(0);" role="button">${_l("start over")}</a>.`;
                this._showAlert(message);
                return;
            }

            var creator = this;

            var elements = this.workingElements.map((element) => creator._elementToJSON(element));

            creator.blocking = true;
            return creator
                .creationFn(elements, name, creator.hideOriginals)
                .always(() => {
                    creator.blocking = false;
                })
                .fail((xhr, status, message) => {
                    creator.trigger("error", {
                        xhr: xhr,
                        status: status,
                        message: _l("An error occurred while creating this collection"),
                    });
                })
                .done(function (response, message, xhr) {
                    creator.trigger("collection:created", response, message, xhr);
                    creator.metric("collection:created", response);
                    if (typeof creator.oncreate === "function") {
                        creator.oncreate.call(this, response, message, xhr);
                    }
                });
        },

        // ------------------------------------------------------------------------ events
        /** set up event handlers on self */
        _setUpBehaviors: function () {
            this.on("error", this._errorHandler);

            this.once("rendered", function () {
                this.trigger("rendered:initial", this);
            });

            this.on("elements:select", function (data) {
                this._renderClearSelected();
            });

            this.on("elements:discard", function (data) {
                var element = data.source.element;
                this.removeElementView(data.source);

                this.workingElements = _.without(this.workingElements, element);
                if (!this.workingElements.length) {
                    this._renderNoElementsLeft();
                }
            });

            //this.on( 'all', function(){
            //    this.info( arguments );
            //});
            return this;
        },

        /** handle errors with feedback and details to the user (if available) */
        _errorHandler: function (data) {
            this.error(data);

            var creator = this;
            var content = data.message || _l("An error occurred");
            if (data.xhr) {
                var xhr = data.xhr;
                var message = data.message;
                if (xhr.readyState === 0 && xhr.status === 0) {
                    content += `: ${_l("Galaxy could not be reached and may be updating.")}${_l(
                        " Try again in a few minutes."
                    )}`;
                } else if (xhr.responseJSON) {
                    content += `:<br /><pre>${JSON.stringify(xhr.responseJSON)}</pre>`;
                } else {
                    content += `: ${message}`;
                }
            }
            creator._showAlert(content, "alert-danger");
        },
        // ........................................................................ elements
        /** reset all data to the initial state */
        reset: function () {
            this._instanceSetUp();
            this._elementsSetUp();
            this.render();
        },

        /** deselect all elements */
        clearSelectedElements: function (ev) {
            this.$(".collection-elements .collection-element").removeClass("selected");
            this.$(".collection-elements-controls > .clear-selected").hide();
        },
        /** track the mouse drag over the list adding a placeholder to show where the drop would occur */
        _dragoverElements: function (ev) {
            //this.debug( '_dragoverElements:', ev );
            ev.preventDefault();

            var $list = this.$list();
            this._checkForAutoscroll($list, ev.originalEvent.clientY);
            var $nearest = this._getNearestElement(ev.originalEvent.clientY);

            //TODO: no need to re-create - move instead
            this.$(".element-drop-placeholder").remove();
            var $placeholder = $('<div class="element-drop-placeholder"></div>');
            if (!$nearest.length) {
                $list.append($placeholder);
            } else {
                $nearest.before($placeholder);
            }
        },

        /** If the mouse is near enough to the list's top or bottom, scroll the list */
        _checkForAutoscroll: function ($element, y) {
            var AUTOSCROLL_SPEED = 2;
            var offset = $element.offset();
            var scrollTop = $element.scrollTop();
            var upperDist = y - offset.top;
            var lowerDist = offset.top + $element.outerHeight() - y;
            if (upperDist >= 0 && upperDist < this.autoscrollDist) {
                $element.scrollTop(scrollTop - AUTOSCROLL_SPEED);
            } else if (lowerDist >= 0 && lowerDist < this.autoscrollDist) {
                $element.scrollTop(scrollTop + AUTOSCROLL_SPEED);
            }
        },

        /** get the nearest element based on the mouse's Y coordinate.
         *  If the y is at the end of the list, return an empty jQuery object.
         */
        _getNearestElement: function (y) {
            var WIGGLE = 4;

            var lis = this.$(".collection-elements li.collection-element").toArray();

            for (var i = 0; i < lis.length; i++) {
                var $li = $(lis[i]);
                var top = $li.offset().top;
                var halfHeight = Math.floor($li.outerHeight() / 2) + WIGGLE;
                if (top + halfHeight > y && top - halfHeight < y) {
                    return $li;
                }
            }
            return $();
        },

        /** drop (dragged/selected elements) onto the list, re-ordering the internal list */
        _dropElements: function (ev) {
            if (ev.originalEvent) {
                ev = ev.originalEvent;
            }
            // both required for firefox
            ev.preventDefault();
            ev.dataTransfer.dropEffect = "move";

            // insert before the nearest element or after the last.
            var $nearest = this._getNearestElement(ev.clientY);
            if ($nearest.length) {
                this.$dragging.insertBefore($nearest);
            } else {
                // no nearest before - insert after last element
                this.$dragging.insertAfter(this.$(".collection-elements .collection-element").last());
            }
            // resync the creator's list based on the new DOM order
            this._syncOrderToDom();
            return false;
        },

        /** resync the creator's list of elements based on the DOM order */
        _syncOrderToDom: function () {
            var creator = this;
            var newElements = [];
            //TODO: doesn't seem wise to use the dom to store these - can't we sync another way?
            this.$(".collection-elements .collection-element").each(function () {
                var id = $(this).attr("data-element-id");

                var element = _.findWhere(creator.workingElements, {
                    id: id,
                });

                if (element) {
                    newElements.push(element);
                } else {
                    console.error("missing element: ", id);
                }
            });
            this.workingElements = newElements;
            this._renderList();
        },
        /** string rep */
        toString: function () {
            return "ListCollectionCreator";
        },
        /** drag communication with element sub-views: dragstart */
        _elementDragstart: function (ev, element) {
            // auto select the element causing the event and move all selected
            element.select(true);
            this.$dragging = this.$(".collection-elements .collection-element.selected");
        },

        /** drag communication with element sub-views: dragend - remove the placeholder */
        _elementDragend: function (ev, element) {
            $(".element-drop-placeholder").remove();
            this.$dragging = null;
        },
    },
    created: {
        /** set up initial options, instance vars, behaviors */
        initialize: function (attributes) {
            this.metric("ListCollectionCreator.initialize", attributes);
            var creator = this;

            _.each(this.defaultAttributes, (value, key) => {
                value = attributes[key] || value;
                creator[key] = value;
            });

            /** unordered, original list - cache to allow reversal */
            creator.initialElements = attributes.elements || [];

            this._setUpCommonSettings(attributes);
            this._instanceSetUp();
            this._elementsSetUp();
            this._setUpBehaviors();
        },
    },
    watch: {},
    components: { DatasetCollectionElementView },
};
</script>
