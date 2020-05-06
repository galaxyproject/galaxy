import Vue from "vue";

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

    removeMissing(outputNames, outputs) {
        this.getAll().forEach((wf_output) => {
            if (!outputNames[wf_output.output_name]) {
                this.remove(wf_output.output_name);
            }
        });
        this.tag(outputs);
    }

    toggle(name, outputs) {
        if (this.exists(name)) {
            this.remove(name);
        } else {
            this.add(name);
        }
        this.tag(outputs);
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

    update(incomingArray, outputs) {
        this.entries = {};
        incomingArray &&
            incomingArray.forEach((entry) => {
                this.add(entry.output_name, entry.label);
            });
        this.tag(outputs);
    }

    tag(outputs) {
        outputs.forEach((o) => {
            Vue.set(o, "isActiveOutput", this.exists(o.name));
        });
    }

    remove(name) {
        delete this.entries[name];
    }

    getAll() {
        return Object.values(this.entries);
    }
}
