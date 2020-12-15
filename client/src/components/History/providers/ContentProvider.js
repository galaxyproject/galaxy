import Vue from "vue";
import { vueRxShortcutPlugin } from "components/plugins";
import { NEVER, BehaviorSubject } from "rxjs";
import { SearchParams } from "../model/SearchParams";

Vue.use(vueRxShortcutPlugin);

// dumb math util
export const clamp = (val, [bottom, top]) => Math.max(bottom, Math.min(top, val));

// simple comparators
export const isDefined = (val) => val !== null && val !== undefined;

// defined, number and finite
export const isValidNumber = (val) => {
    return isDefined(val) && !isNaN(val) && isFinite(val);
};

// validate output variables before rendering
export const validPayload = ({ topRows, bottomRows, totalMatches }) => {
    return isValidNumber(topRows) && isValidNumber(bottomRows) && isValidNumber(totalMatches);
};

// comparator for distinct() style operators inputs are an array of [id, SearchParams]
export const inputsSame = ([a0, a1], [b0, b1]) => {
    return a0 == b0 && SearchParams.equals(a1, b1);
};

export const scrollPosEquals = (a, b) => {
    return a.cursor === b.cursor && a.key === b.key;
};

export const ContentProvider = {
    props: {
        parent: { type: Object, required: true },
        pageSize: { type: Number, default: SearchParams.pageSize },
        debouncePeriod: { type: Number, default: 100 },
        disableWatch: { type: Boolean, default: false },
        disableLoad: { type: Boolean, default: false },
        debug: { type: Boolean, default: false },
    },

    computed: {
        busy() {
            return this.loading || this.scrolling;
        },
    },

    data() {
        return {
            payload: {},
            params: new SearchParams(),
            loading: false,
            scrolling: false,
        };
    },

    created() {
        this.initParams();
        this.initScrollPos();

        const { cache$, loader$, loading$, scrolling$ } = this.initStreams();

        this.listenTo(scrolling$, (val) => (this.scrolling = val));
        this.listenTo(loading$, (val) => (this.loading = val));

        // render output
        if (!this.disableWatch) {
            this.listenTo(cache$, {
                next: (payload) => this.setPayload(payload),
                error: (err) => console.warn("error in cache$", err),
                complete: () => console.warn("why did cache$ complete?"),
            });
        }

        // keep sub to loader which popualates the cache
        if (!this.disableLoad) {
            this.listenTo(loader$, {
                // next: (result) => console.log("loader$ result", result),
                error: (err) => console.warn("error in loader$", err),
                complete: () => console.warn("why did loader$ complete?"),
            });
        }
    },

    methods: {
        initParams() {
            this.params$ = new BehaviorSubject(new SearchParams());
            this.listenTo(this.params$, (val) => (this.params = val));
        },

        initScrollPos() {
            this.scrollPos$ = new BehaviorSubject({ cursor: 0.0, key: null });
        },

        initStreams() {
            console.warn("Override initStreams in ContentProvider");
            return { cache$: NEVER, loader$: NEVER, loading$: NEVER, scrolling$: NEVER };
        },

        /**
         * Handler for the scroller to update its position, either by key or
         * cursor (0-1 value representing how far down it is)
         * @param {object} Object consisting of key and cursor props
         */
        setScrollPos({ cursor = 0.0, key = null } = {}) {
            if (isValidNumber(cursor)) {
                this.scrollPos$.next({ cursor, key });
            }
        },

        /**
         * After bulk operations there is a need to trigger a fresh load.
         */
        manualReload() {
            this.setScrollPos(this.scrollPos$.value);
        },

        /**
         * Exposed method so child components can update the search parameters.
         * @param {SearchParams} newParams Fresh search params
         */
        updateParams(newParams) {
            const val = newParams instanceof SearchParams ? newParams.clone() : new SearchParams(newParams);
            this.params$.next(val);
        },

        /**
         * Render cache observable results to the payload property. It's best to
         * set everything at once to avoid multiple render passes.
         * @param {object} result Cache observable response
         */
        setPayload(newPayload = {}) {
            this.$set(this, "payload", newPayload);
        },
    },

    render() {
        return this.$scopedSlots.default({
            payload: this.payload,

            // local vars/settings/props passthrough
            loading: this.loading,
            scrolling: this.scrolling,
            busy: this.busy,
            params: this.params,
            pageSize: this.pageSize,

            // update methods
            updateParams: this.updateParams,
            setScrollPos: this.setScrollPos,
            manualReload: this.manualReload,
        });
    },
};

export default ContentProvider;
