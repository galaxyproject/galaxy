import IndexFilter from "components/Indices/IndexFilter";

export default {
    components: {
        IndexFilter,
    },
    data() {
        return {
            filter: "",
        };
    },
    computed: {
        isFiltered() {
            return !!this.filter;
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
