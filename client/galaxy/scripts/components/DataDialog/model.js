export class Model {
    constructor(options = {}) {
        this.values = {};
        this.multiple = options.multiple || false;
        this.format = options.format || null;
    }

    /** Adds a new record to the value stack **/
    add(record) {
        if (!this.multiple) {
            this.values = {};
        }
        const key = record && record.id;
        if (key) {
            if (!this.values[key]) {
                this.values[key] = record;
            } else {
                delete this.values[key];
            }
        } else {
            throw "Invalid record with no <id>.";
        }
    }

    /** Returns the number of added records **/
    count() {
        return Object.keys(this.values).length;
    }

    /** Returns true if a record is available for a given key **/
    exists(key) {
        return !!this.values[key];
    }

    /** Finalizes the results from added records **/
    finalize() {
        let results = [];
        Object.values(this.values).forEach((v) => {
            let value = null;
            if (this.format) {
                value = v[this.format];
            } else {
                value = v;
            }
            results.push(value);
        });
        if (results.length > 0 && !this.multiple) {
            results = results[0];
        }
        return results;
    }
}
