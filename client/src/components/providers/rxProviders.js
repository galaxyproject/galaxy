export default {
    props: {
        id: { type: String, required: true },
    },
    data() {
        return {
            item: undefined,
            error: undefined,
        };
    },
    computed: {
        loading() {
            return this.item === undefined && this.error === undefined;
        },
    },
    methods: {
        buildMonitor() {
            throw new Error("define me");
        },
    },
    created() {
        const id$ = this.watch$("id");
        const monitor$ = id$.pipe(this.buildMonitor());

        this.listenTo(monitor$, {
            next: (ds) => {
                this.item = ds;
                this.error = undefined;
            },
            error: (err) => {
                this.error = err.response.err_msg;
                console.warn("error in content monitor", err);
            },
            complete: () => {
                console.log("I should only complete on destroy");
            },
        });
    },
    render() {
        return this.$scopedSlots.default({
            loading: this.loading,
            item: this.item,
            error: this.error,
        });
    },
};
