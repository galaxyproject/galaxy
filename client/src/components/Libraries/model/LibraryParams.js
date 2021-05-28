/**
 * List params for the list of libraries
 */

export class LibraryParams {
    constructor(options = {}) {
        const props = Object.assign({}, LibraryParams.defaults, options);
        Object.assign(this, props);
    }

    // The API is very limited, it's a list of deleted or a list of non-deleted, there is no ability
    // to combine boolean filters, which is... not good

    get searchQuery() {
        const p = new URLSearchParams();
        p.append("deleted", this.showDeleted);
        return p.toString();
    }

    // Client-side filtering

    get stringMatchRe() {
        return new RegExp(`${this.filterText}`, "gi");
    }

    matchLibrary(library) {
        const criteria = [this.matchRestricted, this.matchFilterText];
        return criteria.map((fn) => fn.bind(this, library)).every((fn) => fn());
    }

    matchRestricted(library) {
        if (!this.showRestricted) {
            return library.public == true;
        }
        return true;
    }

    matchFilterText(library) {
        if (this.filterText) {
            const matches = library.textMatchValue.match(this.stringMatchRe);
            return matches && matches.length > 0;
        }
        return true;
    }

    clone(newProps = {}) {
        return LibraryParams.create({ ...this, ...newProps });
    }
}

LibraryParams.defaults = {
    filterText: "",
    showDeleted: false,
    showRestricted: false,
};

// Only export the create function so we never give Vue a mutable object to butcher
// Freeze to avoid Vue's mutation of the model class, hand Vue a fresh immutable object instead
// Will not be a problem in Vue 3 when observability will be a proxy wrapper to the model

LibraryParams.create = (props = {}) => Object.freeze(new LibraryParams(props));
