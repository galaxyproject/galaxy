/**
 * Debugging tool for figuring out what changed to force Vue to re-render
 */

import diff from "deep-diff";

const Monitor = (vm) => {
    const collect = (fields) => fields.reduce((acc, fName) => ({ ...acc, [fName]: vm[fName] }), {});

    const verbs = { N: "Added", D: "Removed", E: "Edited", A: "Array Element" };

    function reportDifferences(label, diffs = []) {
        console.groupCollapsed(label, diffs.length);
        for (const d of diffs) {
            try {
                const { kind, path, index, lhs, rhs, item } = d;
                const prop = path.join(".");
                if (kind == "A") {
                    console.log(verbs[kind], `${prop}[${index}]`, item.rhs);
                } else {
                    console.log(verbs[kind], prop, lhs, rhs);
                }
            } catch (err) {
                console.log("oops", err, d);
            }
        }
        console.groupEnd();
    }

    return {
        // what are we watching?
        props: false,
        data: false,
        computed: false,
        get active() {
            return this.props || this.data || this.computed;
        },

        // last known values
        lastStuff: {},

        // changes
        differences: undefined,

        // set of property names to not bother tracking, handy for large
        // arrays where we don't want every little change
        ignoreProps: new Set(),

        getVals() {
            const computedVals = this.computed ? collect(Object.keys(vm._computedWatchers)) : {};
            const dataVals = this.data ? collect(Object.keys(vm._data)) : {};
            const propVals = this.props ? collect(Object.keys(vm._props)) : {};
            const vals = { ...propVals, ...dataVals, ...computedVals };
            for (const propName of this.ignoreProps) {
                delete vals[propName];
            }
            return vals;
        },

        diff() {
            if (!this.active) return;
            this.differences = diff(this.lastStuff || {}, this.getVals());
        },

        store() {
            if (!this.active) return;
            this.lastStuff = this.getVals();
        },

        report() {
            if (!this.active) return;
            if (this.differences) {
                reportDifferences("updated", this.differences);
                this.differences = undefined;
            }
        },

        ignore(field) {
            this.ignoreProps.add(field);
        },
    };
};

export default {
    beforeCreate() {
        this._monitor = Monitor(this);
    },

    beforeUpdate() {
        this._monitor.diff();
    },

    updated() {
        this._monitor.store();
        this._monitor.report();
    },
};
