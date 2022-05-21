/**
 * Represents an operation that can potentially `clean` the user storage.
 * The concept of `cleaning` here refers to any action that can free up
 * some space in the user storage.
 */
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

    /**
     * Fetches summary information about the total amount of
     * space that can be cleaned/recovered using this operation.
     * @returns {Promise<CleanableSummary>}
     */
    async fetchSummary() {
        return await this._fetchSummary();
    }

    /**
     * Fetches an array of items that can be potentially `cleaned` by this operation.
     * @param {Object} filterOptions The filter options for sorting and pagination of the items.
     * @returns {Promise<Array<Item>>} An array of items that can be potentially `cleaned` and match the filtering params.
     */
    async fetchItems(filterOptions) {
        return await this._fetchItems(filterOptions);
    }

    /**
     * Processes the given items to free up some user storage space and provides a result
     * indicating how much was space was recovered or what errors may have ocurred.
     * @param {Array<Item>} items An array of items to be `cleaned`
     * @returns {Promise<CleanupResult>} The result of the cleanup operation.
     */
    async cleanupItems(items) {
        return await this._cleanupItems(items);
    }
}
