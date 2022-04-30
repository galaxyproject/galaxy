import QueryStringParsing from "utils/query-string-parsing";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: { LoadingSpan },
    data() {
        return {
            currentPage: 1,
            perPage: 20,
            rows: 0,
            loading: true,
        };
    },
    computed: {
        paginationAttrs() {
            return {
                "next-class": "gx-grid-pager-next",
                "prev-class": "gx-grid-pager-prev",
                "first-class": "gx-grid-pager-first",
                "last-class": "gx-grid-pager-last",
                "page-class": "gx-grid-pager-page",
                class: "gx-grid-pager",
                size: "lg",
                "aria-controls": this.tableId,
                "per-page": this.perPage,
                "total-rows": this.rows,
            };
        },
    },
    methods: {
        refresh() {
            this.$root.$emit("bv::refresh::table", this.tableId);
        },
        setRows(data) {
            this.rows = data.headers.total_matches;
            this.loading = false;
        },
        rowsPerPage(defaultPerPage) {
            const queryRowsPerPage = QueryStringParsing.get("rows_per_page");
            return queryRowsPerPage || defaultPerPage;
        },
    },
};
