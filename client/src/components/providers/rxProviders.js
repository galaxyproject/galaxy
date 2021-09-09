export default {
    props: {
        id: { type: String, required: true },
    },
    data() {
        return {
            item: undefined,
        };
    },
    computed: {
        loading() {
            return this.item === undefined;
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
            },
            error: (err) => {
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
        });
    },
};
