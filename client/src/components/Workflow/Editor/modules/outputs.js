import Vue from "vue";

export const allLabels = {};

export class ActiveOutputs {
    constructor() {
        this.entries = {};
    }

    /** Initialize list of active outputs from server response */
    initialize(outputs, incoming) {
        this.outputs = outputs;
        this._refreshIndex();
        incoming &&
            incoming.forEach((entry) => {
                if (entry.label && allLabels[entry.label]) {
                    entry.label = null;
                }
                this.add(entry.output_name, entry.label);
                if (entry.label) {
                    allLabels[entry.label] = true;
                }
            });
    }

    /** Adds a new record to the value stack **/
    add(name, label) {
        if (!this.exists(name)) {
            this.update(name, label);
            return true;
        }
        return false;
    }

    /** Toggle an entry */
    toggle(name) {
        if (this.exists(name)) {
            this.remove(name);
        } else {
            this.add(name);
        }
    }

    /** Change label for an output */
    labelOutput(outputName, newLabel) {
        const activeOutput = this.get(outputName);
        const oldLabel = activeOutput && activeOutput.label;
        if (newLabel == oldLabel) {
            return true;
        }
        if (this.outputsIndex[outputName] && !allLabels[newLabel]) {
            const oldLabel = this.update(outputName, newLabel);
            if (oldLabel && allLabels[oldLabel]) {
                delete allLabels[oldLabel];
            }
            if (newLabel) {
                allLabels[newLabel] = true;
            }
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

    /** Remove an entry given its name */
    remove(name) {
        const activeOutput = this.get(name);
        const activeLabel = activeOutput && activeOutput.label;
        if (activeLabel && allLabels[activeLabel]) {
            delete allLabels[activeLabel];
        }
        delete this.entries[name];
        this._updateOutput(name);
    }

    /** Returns list of all values */
    getAll() {
        return Object.values(this.entries);
    }

    /** Update an active outputs label */
    update(name, label) {
        const activeOutput = this.get(name);
        const oldLabel = activeOutput && activeOutput.label;
        this.entries[name] = {
            output_name: name,
            label: label || null,
        };
        this._updateOutput(name);
        return oldLabel;
    }

    /** Removes all entries which are not in the parsed dictionary of names */
    filterOutputs(names) {
        this.getAll().forEach((wf_output) => {
            if (!names.includes(wf_output.output_name)) {
                this.remove(wf_output.output_name);
            }
        });
        this._refreshIndex();
    }

    /** Update an output */
    _updateOutput(name) {
        const output = this.outputsIndex[name];
        if (output) {
            const activeOutput = this.get(output.name);
            Vue.set(output, "activeOutput", !!activeOutput);
            Vue.set(output, "activeLabel", activeOutput && activeOutput.label);
        }
    }

    /** Refreshes dictionary of outputs */
    _refreshIndex() {
        this.outputsIndex = {};
        this.outputs &&
            this.outputs.forEach((o) => {
                this.outputsIndex[o.name] = o;
                this._updateOutput(o.name);
            });
    }
}
