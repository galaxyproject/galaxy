export class ActiveOutputs {
    constructor() {
        this.entries = {};
    }

    /** Adds a new record to the value stack **/
    add(name, label) {
        if (!this.exists(name)) {
            const output = { output_name: name };
            if (label) {
                output.label = label;
            }
            this.entries[name] = output;
            return true;
        }
        return false;
    }

    /** Returns the number of added records **/
    count() {
        return Object.keys(this.entries).length;
    }

    /**  Return label */
    get(name) {
        return this.entries[name];
    }

    /** Returns true if a record is available for a given key **/
    exists(name) {
        return !!this.entries[name];
    }

    update(incomingArray) {
        this.entries = {};
        incomingArray && incomingArray.forEach((entry) => {
            this.entries[entry.output_name] = entry;
        });
    }

    remove(name) {
        delete this.entries[name];
    }

    getAll() {
        return Object.values(this.entries);
    }
}
