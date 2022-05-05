import IndexFilter from "components/Indices/IndexFilter";

export default {
    components: {
        IndexFilter,
    },
    data() {
        return {
            filter: "",
            implicitFilter: null,
        };
    },
    computed: {
        isFiltered() {
            return !!this.filter;
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
    },
    methods: {
        appendTagFilter(tag, text) {
            this.appendFilter(`${tag}:'${text}'`);
        },
        appendFilter(text) {
            const initialFilter = this.filter;
            if (initialFilter.length === 0) {
                this.filter = text;
            } else if (initialFilter.indexOf(text) < 0) {
                this.filter = `${text} ${initialFilter}`;
            }
        },
    },
};
