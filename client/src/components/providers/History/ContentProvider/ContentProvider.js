import { NEVER } from "rxjs";
import { ScrollPos } from "components/History/model/ScrollPos";
import { SearchParams } from "components/providers/History/SearchParams";
import { isValidNumber } from "utils/validation";

// first emission, emitted when parent (history) or filters changes to reset the view
export const defaultPayload = {
    contents: [],
    targetKey: null,
    startKey: null,
    startKeyIndex: 0,
    topRows: 0,
    bottomRows: 0,
    totalMatches: 0,
};

export const ContentProvider = {
    props: {
        parent: { type: Object, required: true },
        params: { type: SearchParams, default: () => new SearchParams() },
        pageSize: { type: Number, default: SearchParams.pageSize },
        debouncePeriod: { type: Number, default: 1000 },
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
                scrollPos: this.scrollPos,
                loading: this.loading,
                scrolling: this.scrolling,
                busy: this.busy,
                params: this.params,
                pageSize: this.pageSize,

                // update methods
                setScrollPos: this.setScrollPos,
                manualReload: this.manualReload,
            };
        },
    },

    data() {
        return {
            payload: defaultPayload,
            scrollPos: new ScrollPos(),
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
        this.scrollPos$ = this.watch$("scrollPos");
        const { payload$, loading$, scrolling$, resetPos$ = NEVER } = this.initStreams();

        this.listenTo(scrolling$, (val) => (this.scrolling = val));
        this.listenTo(loading$, (val) => (this.loading = val));
        this.listenTo(resetPos$, (pos) => this.setScrollPos(pos));

        // render output
        this.listenTo(payload$, {
            next: (payload) => this.setPayload(payload),
            error: (err) => console.warn("error in cache$", err),
            complete: () => console.warn("why did cache$ complete?"),
        });
    },

    methods: {
        resetScrollPos() {
            this.setScrollPos();
        },

        initStreams() {
            console.warn("Override initStreams in ContentProvider");
            return { payload$: NEVER, loading$: NEVER, scrolling$: NEVER, resetPos$: NEVER };
        },

        /**
         * Handler for the scroller to update its position, either by key or
         * cursor (0-1 value representing how far down it is)
         * @param {object} Object consisting of key and cursor props
         */
        setScrollPos({ cursor = null, key = null } = {}) {
            if (isValidNumber(cursor) || key !== null) {
                this.scrollPos = ScrollPos.create({ cursor, key });
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
            const payload = Object.assign({}, defaultPayload, props);
            this.$set(this, "payload", payload);
        },
    },

    render() {
        return this.$scopedSlots.default(this.slotProps);
    },
};

export default ContentProvider;
