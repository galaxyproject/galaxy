/**
 * The tag model is pretty simple, so this extra file might be overkill, but
 * it's good practice to separate data modeling from data retrieval
 */

import { keyedColorScheme } from "utils/color";

function TagModel(props = {}) {
    this.text = "";

    // special handling for name:thing tags
    if (props.text && props.text.startsWith("#")) {
        props.text = props.text.replace("#", "name:");
    }

    Object.assign(this, props);

    // Need to do Object.defineProperty instead of a class getter to make
    // style enumerable for vue-tags-input
    Object.defineProperty(this, 'style', { 
        enumerable: true,
        get: function() {
            if (this.text.startsWith("name:")) {
        
                let { primary, contrasting, darker } = keyedColorScheme(this.text);
    
                let styles = {
                    'background-color': primary,
                    'color': contrasting,
                    'border-color': darker
                }

                return Object.keys(styles)
                    .map(prop => `${prop}: ${styles[prop]}`)
                    .join(";");
            }
            return "";
        }
    });
}

TagModel.prototype.equals = function(otherTag) {
    return this.text == otherTag.text;
};

TagModel.prototype.toString = function() {
    return this.text;
};

// Public factory

export function createTag(data) {
    let props = {};
    switch (typeof data) {
        case "string":
            props = { text: data };
            break;
        case "object":
            props = Object.assign({}, data);
            break;
    }
    return new TagModel(props);
}

// Returns tags in "newTags" that aren't present in "existingTags"

export const diffTags = (newTags, existingTags) => {
    let newModels = newTags.map(createTag);
    let existingModels = existingTags.map(createTag);
    return newModels.filter(tag => !existingModels.some(st => st.equals(tag)));
};
