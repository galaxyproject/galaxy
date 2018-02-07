define("mvc/tours",["exports","utils/localization","libs/bootstrap-tour"],function(t,e){"use strict";function n(t){var e=c(t);sessionStorage.setItem("activeGalaxyTour",JSON.stringify(t));var n=new i(_.extend({steps:e.steps},u));return n.init(),n.goTo(0),n.restart(),n}function o(t){var e=s+"api/tours/"+t;$.getJSON(e,function(t){n(t)})}function a(){var t=JSON.parse(sessionStorage.getItem("activeGalaxyTour"));if(t&&(t=c(t))&&t.steps&&window&&window.self===window.top){var e=new i(_.extend({steps:t.steps},u));e.init(),e.restart()}}Object.defineProperty(t,"__esModule",{value:!0}),t.ToursView=void 0,t.giveTourWithData=n,t.giveTourById=o,t.activeGalaxyTourRunner=a;var r=function(t){return t&&t.__esModule?t:{default:t}}(e),i=window.Tour,s="undefined"==typeof Galaxy?"/":Galaxy.root,u={storage:window.sessionStorage,onEnd:function(){sessionStorage.removeItem("activeGalaxyTour")},delay:150,orphan:!0},c=function(t){return _.each(t.steps,function(t){t.preclick&&(t.onShow=function(){_.each(t.preclick,function(t){$(t).click()})}),t.postclick&&(t.onHide=function(){_.each(t.postclick,function(t){$(t).click()})}),t.textinsert&&(t.onShown=function(){$(t.element).val(t.textinsert).trigger("change")})}),t},l=Backbone.Model.extend({urlRoot:s+"api/tours"}),d=Backbone.Collection.extend({url:s+"api/tours",model:l}),g=t.ToursView=Backbone.View.extend({title:(0,r.default)("Tours"),initialize:function(){var t=this;this.setElement("<div/>"),this.model=new d,this.model.fetch({success:function(){t.render()},error:function(){console.error("Failed to fetch tours.")}})},render:function(){var t=_.template('<h2>Galaxy Tours</h2>\n<p>This page presents a list of interactive tours available on this Galaxy server.\nSelect any tour to get started (and remember, you can click \'End Tour\' at any time).</p>\n\n<div class="col-12 btn-group" role="group" aria-label="Tag selector">\n    <% _.each(tourtagorder, function(tag) { %>\n    <button class="btn btn-primary tag-selector-button" tag-selector-button="<%- tag %>">\n        <%- tag %>\n    </button>\n    <% }); %>\n</div>\n\n<% _.each(tourtagorder, function(tourtagkey) { %>\n<div tag="<%- tourtagkey %>" style="display: block;">\n    <% var tourtag = tourtags[tourtagkey]; %>\n    <h4>\n        <%- tourtag.name %>\n    </h4>\n    <ul class="list-group">\n    <% _.each(tourtag.tours, function(tour) { %>\n        <li class="list-group-item">\n            <a href="/tours/<%- tour.id %>" class="tourItem" data-tour.id=<%- tour.id %>>\n                <%- tour.name || tour.id %>\n            </a>\n             - <%- tour.attributes.description || "No description given." %>\n             <% _.each(tour.attributes.tags, function(tag) { %>\n                <span class="label label-primary sm-label-pad">\n                    <%- tag.charAt(0).toUpperCase() + tag.slice(1) %>\n                </span>\n             <% }); %>\n        </li>\n    <% }); %>\n    </ul>\n</div>\n<% }); %>'),e={};_.each(this.model.models,function(t){null===t.attributes.tags?(void 0===e.Untagged&&(e.Untagged={name:"Untagged",tours:[]}),e.Untagged.tours.push(t)):_.each(t.attributes.tags,function(n){n=n.charAt(0).toUpperCase()+n.slice(1),void 0===e[n]&&(e[n]={name:n,tours:[]}),e[n].tours.push(t)})});var n=Object.keys(e).sort();this.$el.html(t({tours:this.model.models,tourtags:e,tourtagorder:n})).on("click",".tourItem",function(t){t.preventDefault(),o($(this).data("tour.id"))}).on("click",".tag-selector-button",function(t){var e=$(t.target),n="block",o=e.attr("tag-selector-button");e.toggleClass("btn-primary"),e.toggleClass("btn-secondary"),e.hasClass("btn-secondary")&&(n="none"),$("div[tag='"+o+"']").css({display:n})})}});t.default={ToursView:g,giveTourWithData:n,giveTourById:o,activeGalaxyTourRunner:a}});