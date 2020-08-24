


/*==============================================================================
TODO:
    use proper Element model and not just json
    straighten out createFn, collection.createHDCA
    possibly stop using modals for this
    It would be neat to do a drag and drop

==============================================================================*/
/** A view for both DatasetDCEs and NestedDCDCEs
 *  (things that implement collection-model:DatasetCollectionElementMixin)
 */
// var DatasetCollectionElementView = Backbone.View.extend(BASE_MVC.LoggableMixin).extend({

//     render: function () {
//         this.dragStartHandler = _.bind(this._dragstart, this);
//         this.dragEndHandler = _.bind(this._dragend, this);
//         var handle = this.$el
//             .attr("data-element-id", this.element.id)
//             .attr("draggable", true)
//             .html(this.template({ element: this.element }))
//             .get(0);
//         handle.addEventListener("dragstart", this.dragStartHandler, false);
//         handle.addEventListener("dragend", this.dragEndHandler, false);
//         if (this.selected) {
//             this.$el.addClass("selected");
//         }
//         return this;
//     },

//     events: {
//         click: "_click",
//         "click .name": "_clickName",
//         "click .discard": "_clickDiscard",

//         dragover: "_sendToParent",
//         drop: "_sendToParent",
//     },

// });

// ============================================================================
/** An interface for building collections.
 */
// var ListCollectionCreator = Backbone.View.extend(BASE_MVC.LoggableMixin)
//     .extend(baseCreator)
//     .extend({

//         //_dragenterElements : function( ev ){
//         //    //this.debug( '_dragenterElements:', ev );
//         //},
//         //TODO: if selected are dragged out of the list area - remove the placeholder - cuz it won't work anyway
//         // _dragleaveElements : function( ev ){
//         //    //this.debug( '_dragleaveElements:', ev );
//         // },


//         // ------------------------------------------------------------------------ templates
//         //TODO: move to require text plugin and load these as text
//         //TODO: underscore currently unnecc. bc no vars are used
//         //TODO: better way of localizing text-nodes in long strings
//         /** underscore template fns attached to class */
//         templates: _.extend({}, baseCreator._creatorTemplates, {
//             /** the header (not including help text) */


//             /** shown in list when all elements are discarded */
//             invalidElements: _.template(
//                 [
//                     _l("The following selections could not be included due to problems:"),
//                     "<ul><% _.each( problems, function( problem ){ %>",
//                     "<li><b><%- problem.element.name %></b>: <%- problem.text %></li>",
//                     "<% }); %></ul>",
//                 ].join("")
//             ),

//             /** shown in list when all elements are discarded */
//             noElementsLeft: _.template(
//                 [
//                     '<li class="no-elements-left-message">',
//                     _l("No elements left! "),
//                     _l("Would you like to "),
//                     '<a class="reset" href="javascript:void(0)" role="button">',
//                     _l("start over"),
//                     "</a>?",
//                     "</li>",
//                 ].join("")
//             ),

//             /** a simplified page communicating what went wrong and why the user needs to reselect something else */
//             invalidInitial: _.template(
//                 [
//                     '<div class="header flex-row no-flex">',
//                     '<div class="alert alert-warning" style="display: block">',
//                     '<span class="alert-message">',
//                     "<% if( _.size( problems ) ){ %>",
//                     _l("The following selections could not be included due to problems"),
//                     ":",
//                     "<ul><% _.each( problems, function( problem ){ %>",
//                     "<li><b><%- problem.element.name %></b>: <%- problem.text %></li>",
//                     "<% }); %></ul>",
//                     "<% } else if( _.size( elements ) < 1 ){ %>",
//                     _l("No datasets were selected"),
//                     ".",
//                     "<% } %>",
//                     "<br />",
//                     _l("At least one element is needed for the collection"),
//                     ". ",
//                     _l("You may need to "),
//                     '<a class="cancel-create" href="javascript:void(0)" role="button">',
//                     _l("cancel"),
//                     "</a> ",
//                     _l("and reselect new elements"),
//                     ".",
//                     "</span>",
//                     "</div>",
//                     "</div>",
//                     '<div class="footer flex-row no-flex">',
//                     '<div class="actions clear vertically-spaced">',
//                     '<div class="other-options float-left">',
//                     '<button class="cancel-create btn" tabindex="-1">',
//                     _l("Cancel"),
//                     "</button>",
//                     // _l( 'Create a different kind of collection' ),
//                     "</div>",
//                     "</div>",
//                     "</div>",
//                 ].join("")
//             ),
//         }),

//     });