/**
 * Initialization functions for tagging component. This is a bridge between the
 * python-rendered page and an eventual component-based architecture. These
 * functions pass in a set of python-rendered configuration variables and
 * instantiate a component. In the near future, we'll just pass props to the
 * component from the parent components and do away with this hybrid approach.
 */

import StandardTags from "./StandardTags";
import GalaxyTags from "./GalaxyTags";
import { mountVueComponent } from "utils/mountVueComponent";
import { getGalaxyInstance } from "app";

/**
 * General mount function for the tags that were previously rendered
 * by the tagging_common.mako file
 */
export const mountTaggingComponent = mountVueComponent(StandardTags);

/**
 * Mount function for the tags that appear in several of the
 * backbone grids.
 * 
 * @param {Object} model Backbone model object
 * @param {Object} el DOM element container
 */
export function mountGridTags(model, el) {
    
    let propsData = { 
        useToggleLink: false, 
        value: model.attributes.tags 
    };

    let mount = mountVueComponent(GalaxyTags);
    let vm = mount(propsData, el);

    // when the tags change, save the model
    vm.$on("input", (tags) => model.save({ tags }));

    // when the little variable text input changes, re-filter
    vm.$on("tag-input-changed", function(txt) {
        let Galaxy = getGalaxyInstance();
        this.autocompleteItems = Galaxy.user.get("tags_used")
            .filter(label => label.includes(txt));
    });
}
