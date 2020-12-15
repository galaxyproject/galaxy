/**
 * Renderless component, used to debounce various types of form inputs
 */

import Vue from "vue";
import VueRx from "vue-rx";
import { filter, debounceTime, distinctUntilChanged, finalize } from "rxjs/operators";
import { vueRxShortcuts } from "./plugins";

Vue.use(VueRx);

export default {
    mixins: [vueRxShortcuts],
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
    beforeMount() {
        const debounced$ = this.watch$("incomingValue").pipe(
            debounceTime(this.delay),
            distinctUntilChanged(),
            filter((val) => val !== null && val !== this.value),
            finalize(() => this.sendUpdate(this.incomingValue))
        );
        this.$subscribeTo(debounced$, (val) => this.sendUpdate(val));
    },
    render() {
        return this.$scopedSlots.default({
            value: this.value,
            input: (e) => {
                // Of course Vue Bootstrap does not conform to the standard
                // event object, so we have to check for their incompetence
                // if we want to use this with the Vue Bootstrap components
                // console.log("input event handler", e, arguments);
                this.incomingValue = e && e.target ? e.target.value : e;
            },
        });
    },
};
