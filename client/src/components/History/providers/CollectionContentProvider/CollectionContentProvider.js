/**
 * Same basic format as historyContentProvider, but it should be simpler than
 * the history because:
 *
 * 1. Collections are immutable after creation so they don't change over time,
 *    meaning there is no polling and no need to do "random access" as we do for
 *    histories since we can just limit/offset to reach everything since the
 *    total matches count will always be the same. A "total matches" exists in
 *    the basic content record in the form of "element_count", and we already
 *    have that value in the DSC which is passed in.
 *
 * 2. There is no filtering for collections on the server so all we can do is
 *    page through the results.
 */

import { DatasetCollection } from "../../model";
import { ContentProvider } from "../ContentProvider";
import { processCollectionStreams } from "./processCollectionStreams";

export default {
    mixins: [ContentProvider],

    computed: {
        dsc() {
            if (this.parent instanceof DatasetCollection) {
                return this.parent;
            }
            return new DatasetCollection(this.parent);
        },
    },

    watch: {
        dsc(newDsc, oldDsc) {
            if (!(newDsc.id == oldDsc.id)) {
                this.resetScrollPos();
            }
        },
    },

    methods: {
        initStreams() {
            const { debouncePeriod, pageSize, params$, scrollPos$ } = this;
            const dsc$ = this.watch$("dsc", true);
            const sources = { params$, dsc$, scrollPos$ };
            const settings = { debouncePeriod, pageSize };
            return processCollectionStreams(sources, settings);
        },
    },
};
