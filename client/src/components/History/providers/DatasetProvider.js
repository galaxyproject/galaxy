// Simple dataset provider, looks at api for result, renders to slot prop
import axios from "axios";
import { prependPath } from "utils/redirect"



export default {
    props: {
        id: { type: String, required: true }
    },
    data() {
        return {
            loading: false,
            dataset: null
        }
    },
    computed: {
        // Without knowing how this fits into yoru requirements, I'm not sure
        // exactly what IDs you have access to , but all you'd really need to
        // change is the input props (above) and this url generation
        url() {
            return prependPath(`/api/dataset/${this.id}`);
        }
    },
    watch: {
        watch: {
            id: {
                immediate: true,
                handler(newVal, oldVal) {
                    if (newVal !== oldVal) {
                        this.load();
                    }
                }
            }
        }
    },
    methods: {
        async load() {
            this.loading = true;
            const result = await axios.get(this.url);
            this.dataset = result;
            this.loading = false;
        },
        async save(newProps) {
            this.loading = true;
            const result = await axios.put(this.url, newProps);
            this.dataset = result;
            this.loading = false;
        },
    },
    render() {
        return this.$scopedSlots.default({
            loading: this.loading,
            dataset: this.dataset,
            save: this.save
        });
    },
}
