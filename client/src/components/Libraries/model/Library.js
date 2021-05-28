/**
 * Model for an individual library
 */

export class Library {
    constructor(options = {}) {
        const props = Object.assign({}, Library.defaults, options);
        Object.assign(this, props);
    }

    get textMatchValue() {
        const { name = "", description = "", synopsis = "" } = this;
        return `${name} ${description} ${synopsis}`.trim();
    }

    clone(newProps = {}) {
        return Library.create({ ...this, ...newProps });
    }
}

Library.defaults = {
    public: true,
    name: "",
    description: "",
    synopsis: "",
};

// Only export the creation function so we make sure that we're
// never making a mutable object for Vue to butcher
Library.create = (props = {}) => Object.freeze(new Library(props));
