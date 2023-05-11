import QueryStringParsing from "utils/query-string-parsing";
import LoadingSpan from "components/LoadingSpan";
import { errorMessageAsString } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export default {
    components: { LoadingSpan },
    props: {
        defaultPerPage: {
            type: Number,
            required: false,
            default: null,
        },
    },
    data() {
        return {
            items: [],
            root: getAppRoot(),
            currentPage: 1,
            perPage: this.defaultPerPage || 20,
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
                align: "center",
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
                items: this.tableProvider,
            };
        },
        alertAttrs() {
            return {
                class: "index-grid-message",
                variant: this.messageVariant,
                show: this.showMessage,
            };
        },
        showMessage() {
            return !!this.message;
        },
    },
    methods: {
        async tableProvider(ctx) {
            ctx.root = this.root;
            const extraParams = this.dataProviderParameters;
            const promise = this.dataProvider(ctx, this.setRows, extraParams).catch(this.onError);
            const items = await promise;
            (items || []).forEach(this.decorateData);
            this.items = items;
            return items;
        },
        decorateData(item) {},
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
