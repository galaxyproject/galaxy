/**
 * A provider for a single dataset, checks the cache, then does a query on expand that retrieves a
 * newer version if one exists
 */

import { objectNeedsProps } from "utils/objectNeedsProps";
import { getContentByTypeId, cacheContent } from "../caching";
import { getContentDetails } from "../model/queries";
import { Dataset } from "../model";

export const datasetContentValidator = objectNeedsProps(["history_id", "type_id", "id", "history_content_type"]);

export default {
    props: {
        item: {
            type: Object,
            required: true,
            validator: datasetContentValidator,
        },
    },

    data() {
        return {
            rawData: null,
        };
    },

    computed: {
        dataset() {
            const props = this.rawData || this.item;
            return props ? new Dataset(props) : null;
        },
        loaded() {
            return this.dataset?.isFullDataset || false;
        },
    },

    methods: {
        async loadFromCache() {
            const { history_id, type_id } = this.item;
            const localContent = await getContentByTypeId(history_id, type_id);
            return localContent || null;
        },
        async loadFromServer() {
            const { history_id, id, history_content_type } = this.item;
            const rawServerContent = await getContentDetails({ history_id, id, history_content_type });
            this.rawData = await cacheContent(rawServerContent, true);
        },
    },

    async created() {
        this.rawData = await this.loadFromCache();
    },

    render() {
        return this.$scopedSlots.default({
            loaded: this.loaded,
            dataset: this.dataset,
            load: this.loadFromServer,
        });
    },
};
