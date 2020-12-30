import { vueRxShortcuts } from "components/plugins";
import { datasetMonitor } from "./monitors";

export default {
    mixins: [vueRxShortcuts],
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
        }
    },
    // prettier-ignore
    created() {
        const id$ = this.watch$("id");
        const monitor$ = id$.pipe(datasetMonitor());
        
        this.listenTo(monitor$, {
            next: (ds) => {
                this.item = ds;
            },
            error: (err) => {
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
