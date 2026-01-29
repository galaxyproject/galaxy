/**
 * The tag model is pretty simple, so this extra file might be overkill, but
 * it's good practice to separate data modeling from data retrieval
 */

import { keyedColorScheme } from "utils/color";

// Valid tag regex. The basic format here is a tag name with optional subtags
// separated by a period, and then an optional value after a colon.
export const VALID_TAG_RE = /^([^\s.:])+(\.[^\s.:]+)*(:\S+)?$/;

export class TagModel {
    /**
     * @param {string || object} data
     */
    constructor(data) {
        let props = {};

        switch (typeof data) {
            case "string":
                props = { text: data };
                break;
            case "object":
                props = data;
                break;
        }

        Object.assign(this, props);

        this.text = props.text ?? "";
        this.label = this.text.replace(/^name:/, "#");
        this.text = this.text.replace(/^#/, "name:");
        this.style = "";

        if (this.text.startsWith("name:")) {
            this.style += "font-weight: bold;";
        }

        const { primary, darker } = keyedColorScheme(this.text);

        this.style += `background-color: ${primary};`;
        this.style += "color: black;";
        this.style += `border-color: ${darker};`;

        this.valid = VALID_TAG_RE.test(this.text);
    }

    equals(otherTag) {
        return this.text === otherTag.text;
    }

    toString() {
        return this.text;
    }
}

// Public factory

export function createTag(data) {
    return new TagModel(data);
}

// Returns tags in "newTags" that aren't present in "existingTags"

export const diffTags = (newTags, existingTags) => {
    const newModels = newTags.map(createTag);
    const existingModels = existingTags.map(createTag);
    return newModels.filter((tag) => !existingModels.some((st) => st.equals(tag)));
};
