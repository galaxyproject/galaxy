/**
 * Generic list-storage container wraps a Map, returns new value on add/delete
 * so it's useful as an observable wrapper.
 */
export class ListStorage {

    constructor(keySelector, items = new Map()) {
        this.keySelector = keySelector;
        this.items = items;
    }

    add(item) {
        const newItems = new Map(this.items);
        const key = this.keySelector(item);
        newItems.set(key, item);
        return new ListStorage(this.keySelector, newItems);
    }

    remove(item) {
        const newItems = new Map(this.items);
        const key = this.keySelector(item);
        newItems.delete(key);
        return new ListStorage(this.keySelector, newItems);
    }

    bulkLoad(items = []) {
        const entries = items.map(item => {
            return [ this.keySelector(item), item ];
        });
        return new ListStorage(this.keySelector, new Map(entries));
    }

    get size() {
        return this.items.size;
    }

    has(item) {
        const key = this.keySelector(item);
        return this.hasKey(key);
    }

    hasKey(key) {
        return this.items.has(key);
    }

    [Symbol.iterator]() {
        return this.items.values();
    }

}

export default ListStorage;
