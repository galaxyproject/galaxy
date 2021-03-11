import { NEVER, BehaviorSubject } from "rxjs";
import { SearchParams, ScrollPos } from "../model";
import { isValidNumber } from "./helpers";

export default {
    props: {
        parent: { type: Object, required: true },
        params: { type: SearchParams, default: () => new SearchParams() },
        pageSize: { type: Number, default: SearchParams.pageSize },
        debouncePeriod: { type: Number, default: 250 },
        disableWatch: { type: Boolean, default: false },
        debug: { type: Boolean, default: false },
    },

    computed: {
        busy() {
            return this.loading || this.scrolling;
        },
        slotProps() {
            return {
                // actual content delivery
                payload: this.payload,

                // local vars/settings/props passthrough
                loading: this.loading,
                scrolling: this.scrolling,
                busy: this.busy,
                params: this.params,
                pageSize: this.pageSize,

                // update methods
                setScrollPos: this.setScrollPos,
            };
        },
    },

    data() {
        return {
            payload: {},
            loading: false,
            scrolling: false,
        };
    },

    watch: {
        params(newParams, oldParams) {
            if (!SearchParams.equals(newParams, oldParams)) {
                this.resetScrollPos();
            }
        },
    },

    created() {
        this.params$ = this.watch$("params");
        this.scrollPos$ = new BehaviorSubject(ScrollPos.create());
        const { payload$, loading$, scrolling$ } = this.initStreams();

        this.listenTo(scrolling$, (val) => (this.scrolling = val));
        this.listenTo(loading$, (val) => (this.loading = val));

        // render output
        if (!this.disableWatch) {
            this.listenTo(payload$, {
                next: (payload) => this.setPayload(payload),
                error: (err) => console.warn("error in cache$", err),
                complete: () => console.warn("why did cache$ complete?"),
            });
        }
    },

    methods: {
        resetScrollPos() {
            this.scrollPos$.next(ScrollPos.create());
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
                this.scrollPos$.next(ScrollPos.create({ cursor, key }));
            }
        },

        /**
         * After bulk operations there is a need to trigger a fresh load.
         */
        manualReload() {
            this.setScrollPos(this.scrollPos$.value);
        },

        /**
         * Render cache observable results to the payload property. It's best to
         * set everything at once to avoid multiple render passes.
         * @param {object} result Cache observable response
         */
        setPayload(props = {}) {
            const payloadDefaults = { contents: [], startKey: null, topRows: 0, bottomRows: 0, totalMatches: 0 };
            const newPayload = Object.assign({}, payloadDefaults, props);
            this.$set(this, "payload", newPayload);
        },
    },

    render() {
        return this.$scopedSlots.default(this.slotProps);
    },
};
