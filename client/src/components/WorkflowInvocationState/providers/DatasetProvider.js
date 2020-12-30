import { vueRxShortcuts } from "components/plugins";
import { datasetMonitor } from "./monitors";

export default {
    mixins: [vueRxShortcuts],
    props: {
        id: { type: String, required: true },
    },
    data() {
        return {
            loading: true,
            item: undefined,
        };
    },
    // prettier-ignore
    created() {
        const monitor$ = this.watch$("id").pipe(
            datasetMonitor()
        );
        this.listenTo(monitor$, {
            next: (ds) => {
                this.loading = false;
                this.item = ds;
            },
            error: (err) => {
                this.loading = false;
                console.warn("error in dataset monitor", err);
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
