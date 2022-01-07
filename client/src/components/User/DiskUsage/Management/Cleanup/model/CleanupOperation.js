export class CleanupOperation {
    constructor(data) {
        this._id = data.id;
        this._name = data.name;
        this._description = data.description;
        this._fetchSummary = data.fetchSummary;
        this._fetchItems = data.fetchItems;
        this._cleanupItems = data.cleanupItems;
    }

    /**
     * The ID of this cleanup operation.
     * @returns {String}
     */
    get id() {
        return this._id;
    }

    /**
     * The name of this cleanup operation.
     * @returns {String}
     */
    get name() {
        return this._name;
    }

    /**
     * The description of this cleanup operation.
     * @returns {String}
     */
    get description() {
        return this._description;
    }

    async fetchSummary() {
        return await this._fetchSummary();
    }

    async fetchItems(offset, limit) {
        return await this._fetchItems(offset, limit);
    }

    async cleanupItems(items) {
        return await this._cleanupItems(items);
    }
}
