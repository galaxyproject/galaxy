/**
 * The tag model is pretty simple, so this extra file might be overkill, but
 * it's good practice to separate data modeling from data retrieval
 */


// model prototype

function TagModel(props = {}) {
    this.text = "";
    Object.assign(this, props);
}

TagModel.prototype.equals = function(otherTag) {
    return (this.text == otherTag.text);
}

TagModel.prototype.toString = function() {
    return this.text;
}


// Public factory

export function createTag(data) {
    let props = {};
    switch (typeof(data)) {
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
}
