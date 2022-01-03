import { CleanupCategory } from "../../model";
import { cleanupCategories } from "./categories";

export class ResourceCleanupManager {
    constructor() {
        this._categories = this.loadCategories();
        this._operationsMap = this.buildOperationsMap();
    }

    get categories() {
        return this._categories;
    }

    getOperationById(id) {
        return this._operationsMap[id];
    }

    loadCategories() {
        return cleanupCategories.map((category) => new CleanupCategory(category));
    }

    buildOperationsMap() {
        const operations = new Map();
        this._categories.forEach((category) => {
            category._operations.forEach((operation) => {
                if (operations.has(operation.id)) {
                    throw new Error(`Duplicated operation ${operation.id} found. Please use a unique ID.`);
                }
                operations[operation.id] = operation;
            });
        });
        return operations;
    }

    static create() {
        return new ResourceCleanupManager();
    }
}
