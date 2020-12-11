import Vue from "vue";
import VueRx from "vue-rx";
import { pluck } from "rxjs/operators";

Vue.use(VueRx);

const defaultNext = (label) => (result) => {
    if (label) console.log(`[${label}] next`, result);
};

const defaultErr = (label) => (err) => {
    if (label) console.warn(`[${label}] error`, err);
};

const defaultComplete = (label) => () => {
    if (label) console.log(`[${label}] complete`);
};

export const vueRxShortcuts = {
    methods: {
        /**
         * Watch any property, adds debugging tag and assumes you want newValue,
         * this is usually what we want and shorter than typing it every time
         *
         * @param {string} propName Member to watch
         * @param {boolean} immediate Check right now?
         * @returns Observable of new value
         */
        watch$(propName, immediate = true) {
            const opts = { immediate };
            // prettier-ignore
            return this.$watchAsObservable(propName, opts).pipe(
                pluck("newValue")
            );
        },

        /**
         * Generic subscriber, subscribes to observable and disposes when
         * component unloads. Assumes you don't need to manage the response
         * data, if you do just use $subscribeTo instead
         *
         * @param {obervable} obs$ Observable to subscribe to
         * @param {string} label Debugging label
         */
        listenTo(obs$, cfg = {}) {
            const config = cfg instanceof Function ? { next: cfg } : cfg;
            const {
                label = null,
                next = defaultNext(label),
                error = defaultErr(label),
                complete = defaultComplete(label),
            } = config;

            if (!obs$) return;
            this.$subscribeTo(obs$, next, error, complete);
        },
    },
};
