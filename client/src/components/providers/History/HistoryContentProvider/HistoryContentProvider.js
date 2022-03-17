import { ContentProvider, processContentStreams } from "../ContentProvider";
import { contentPayload } from "./contentPayload";

export default {
    mixins: [ContentProvider],

    props: {
        disablePoll: { type: Boolean, default: false },
    },

    computed: {
        history() {
            return this.parent;
        },
    },

    watch: {
        history(newHistory, oldHistory) {
            if (!(newHistory.id == oldHistory.id)) {
                this.resetScrollPos();
            }
        },
    },

    methods: {
        initStreams() {
            const { disablePoll, debouncePeriod, pageSize, params$, scrollPos$, debug } = this;
            const parent$ = this.watch$("history");
            const sources = { params$, parent$, scrollPos$ };
            const settings = { disablePoll, debouncePeriod, pageSize, debug };
            return processContentStreams(contentPayload, sources, settings);
        },
    },
};
