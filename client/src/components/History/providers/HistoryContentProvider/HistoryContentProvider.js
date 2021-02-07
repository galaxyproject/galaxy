import { ContentProvider } from "../ContentProvider";
import { processHistoryStreams } from "./processHistoryStreams";

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
            const { disablePoll, debouncePeriod, pageSize, params$, scrollPos$ } = this;
            const history$ = this.watch$("history");
            const sources = { params$, history$, scrollPos$ };
            const settings = { disablePoll, debouncePeriod, pageSize };
            return processHistoryStreams(sources, settings);
        },
    },
};
