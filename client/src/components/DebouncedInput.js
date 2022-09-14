/**
 * Renderless component, used to debounce various types of form inputs
 */

import { filter, debounceTime, distinctUntilChanged, finalize } from "rxjs/operators";

export default {
    props: {
        value: { required: true },
        delay: { type: Number, required: false, default: 500 },
    },
    data() {
        return {
            previousEmit: null,
            incomingValue: null,
        };
    },
    methods: {
        sendUpdate(val) {
            if (val !== this.previousEmit) {
                this.$emit("input", val);
                this.previousEmit = val;
            }
        },
    },
    watch: {
        incomingValue(val) {
            if (this.delay === 0) {
                this.sendUpdate(val);
            }
        },
    },
    beforeMount() {
        if (this.delay !== 0) {
            const debounced$ = this.watch$("incomingValue").pipe(
                debounceTime(this.delay),
                distinctUntilChanged(),
                filter((val) => val !== null && val !== this.value),
                finalize(() => this.sendUpdate(this.incomingValue))
            );
            this.$subscribeTo(debounced$, (val) => this.sendUpdate(val));
        }
    },
    render() {
        return this.$scopedSlots.default({
            value: this.value,
            input: (e) => {
                // Vue Bootstrap does not conform to the standard
                // event object format, so check there first
                this.incomingValue = e && e.target ? e.target.value : e;
            },
        });
    },
};
