import { CleanupOperation } from ".";

export class CleanupCategory {
    constructor(data) {
        this._id = data.id;
        this._name = data.name;
        this._operations = data.operations.map((op) => new CleanupOperation(op));
    }

    /**
     * The ID of this category.
     * @returns {String}
     */
    get id() {
        return this._id;
    }

    /**
     * The name of this category.
     * @returns {String}
     */
    get name() {
        return this._name;
    }

    /**
     * The collection of cleanup operations associated with
     * this category.
     */
    get operations() {
        return this._operations;
    }
}
