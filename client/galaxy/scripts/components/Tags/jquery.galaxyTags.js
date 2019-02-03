/**
 * A jquery plugin that mounts a Vue component for use in legacy Backbone views
 * TODO: Remove this frankencode once we're not using jquery
 */

/*
library-dataset-view.js
    this.select_extension.$el.select2("data").id

tag.js
    this.$input().select2({
        placeholder: "Add tags",
        width: this.workflow_mode ? this.width : this.select_width,
        tags: function() {
            // initialize possible tags in the dropdown based on all the tags the user has used so far
            return self._getTagsUsed();
        }
    });

ui-select-default.js
    this.$select.select2("open");
    this.$select.select2("destroy");

*/

import jQuery from "jqueryVendor";
import GridTags from "./GridTags";
import { mountVueComponent } from "utils/mountVueComponent";

// vm lookup
const vmCache = new Map();
const mount = mountVueComponent(GridTags);

(function($) {
    
    function getVm(settings, el) {
        if (!vmCache.has(el)) {
            
            console.log("Initialize component");
            console.log("Tag func, autocompleteOptions", settings.tags());

            let tags = el.value ? el.value.split(",") : [];
            let autocompleteOptions = settings.tags ? settings.tags() : [];
            let propsData = { tags, autocompleteOptions };

            vmCache.set(el, mount(propsData, el));
        }
        return vmCache.get(el);
    }

    $.fn.galaxyTags = function(options = {}) {

        let settings = Object.assign({}, options);
        
        return this.each(function(i, el) {
            console.group("galaxyTags");
            console.log("arguments", arguments);
            console.log("container", el);
            console.log("settings", settings);
            let vm = getVm(settings, el);
            console.log("vm", vm);
            console.groupEnd();
        })
    }

})(jQuery);
