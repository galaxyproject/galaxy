/**
 * Model for an individual library
 */

import hash from "object-hash";

export class Library {
    constructor(options = {}) {
        const validOptions = Object.entries(options).reduce((clean, [propName, val]) => {
            if (!Library.restrictedKeys.has(propName)) {
                return { ...clean, [propName]: val };
            }
            return clean;
        }, {});
        const props = Object.assign({}, Library.defaults, validOptions);
        Object.assign(this, props);
    }

    // Equivalence

    get hashKey() {
        return hash(this, {
            excludeKeys: (key) => Library.restrictedKeys.has(key),
        });
    }

    equals(to = {}) {
        const otherLib = to instanceof Library ? to : Library.create(to);
        return this.hashKey == otherLib.hashKey;
    }

    clone(newProps = {}) {
        return Library.create({ ...this, ...newProps });
    }

    // Search props

    get textMatchValue() {
        const { name = "", description = "", synopsis = "" } = this;
        return `${name} ${description} ${synopsis}`.trim();
    }
}

Library.restrictedKeys = new Set(Object.getOwnPropertyNames(Library.prototype));

Library.defaults = {
    public: true,
    name: "",
    description: "",
    synopsis: "",
};

// Only export the creation function so we make sure that we're
// never making a mutable object for Vue to butcher
Library.create = (props = {}) => Object.freeze(new Library(props));
