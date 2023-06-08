import IndexFilter from "components/Indices/IndexFilter";

export default {
    components: {
        IndexFilter,
    },
    props: {
        inputDebounceDelay: {
            type: Number,
            default: 500,
        },
    },
    data() {
        return {
            filter: "",
            implicitFilter: null,
            helpHtml: null,
        };
    },
    computed: {
        isFiltered() {
            return Boolean(this.filter);
        },
        effectiveFilter() {
            let filter = this.filter;
            const implicitFilter = this.implicitFilter;
            if (implicitFilter && filter) {
                filter = `${implicitFilter} ${filter}`;
            } else if (implicitFilter) {
                filter = implicitFilter;
            }
            return filter;
        },
        filterAttrs() {
            return {
                "debounce-delay": this.inputDebounceDelay,
                placeholder: this.titleSearch,
                "help-html": this.helpHtml,
            };
        },
    },
    methods: {
        appendTagFilter(tag, text) {
            this.appendFilter(`${tag}:'${text}'`);
        },
        appendFilter(text, replace = false) {
            const initialFilter = replace ? "" : this.filter;
            if (initialFilter.length === 0) {
                this.filter = text;
            } else if (initialFilter.indexOf(text) < 0) {
                this.filter = `${text} ${initialFilter}`;
            }
        },
    },
};
