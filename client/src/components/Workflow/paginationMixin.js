import QueryStringParsing from "utils/query-string-parsing";
import LoadingSpan from "components/LoadingSpan";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: { LoadingSpan },
    data() {
        return {
            currentPage: 1,
            perPage: 20,
            rows: 0,
            loading: true,
            message: null,
            messageVariant: null,
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
        indexTableAttrs() {
            return {
                hover: true,
                striped: true,
                "caption-top": true,
                fixed: true,
                "show-empty": true,
                id: this.tableId,
                "per-page": this.perPage,
                "current-page": this.currentPage,
            };
        },
        showMessage() {
            return !!this.message;
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
        onSuccess: function (message) {
            this.message = message;
            this.messageVariant = "success";
        },
        onError: function (message) {
            this.message = errorMessageAsString(message);
            this.messageVariant = "danger";
        },
    },
};
