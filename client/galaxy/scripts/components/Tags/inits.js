/**
 * Initialization functions for tagging component. This is a bridge between the
 * python-rendered page and an eventual component-based architecture. These
 * functions pass in a set of python-rendered configuration variables and
 * instantiate a component. In the near future, we'll just pass props to the
 * component from the parent components and do away with this hybrid approach.
 */

import StandardTags from "./StandardTags";
import ModelTags from "./ModelTags.vue";
import { mountVueComponent } from "utils/mountVueComponent";

/**
 * General mount function for the tags that were previously rendered
 * by the tagging_common.mako file
 */
export const mountTaggingComponent = mountVueComponent(StandardTags);

/**
 * Mount when a backbone model is available
 */
export const mountModelTags = mountVueComponent(ModelTags);
