<!-- When a collection is selected, the panel shows the contents of that selection -->

<template>
    <DscProvider :is-root="isRoot" :collection="selectedCollection" v-slot="{ dsc }">
        <CollectionContentProvider
            v-if="dsc"
            :parent="dsc"
            v-slot="{
                payload: {
                    contents = [],
                    startKey = null,
                    topRows = 0,
                    bottomRows = 0,
                    totalMatches = 0
                },
                busy: loading,
                params,
                pageSize,
                updateParams,
                setScrollPos,
            }"
        >
            <Layout>
                <template v-slot:nav>
                    <TopNav
                        :history="history"
                        :selected-collections="selectedCollections"
                        :show-tags.sync="showTags"
                        :show-filter.sync="showFilter"
                        v-on="$listeners"
                    />
                </template>

                <template v-slot:details>
                    <Details
                        :dsc="dsc"
                        :writable="writable"
                        :show-tags.sync="showTags"
                        :show-filter.sync="showFilter"
                        @update:dsc="updateDsc(dsc, $event)"
                    />
                </template>

                <template v-slot:listing>
                    <VirtualScroller
                        key-field="element_index"
                        :item-height="36"
                        :items="contents"
                        :scroll-to="startKey"
                        :top-placeholders="topRows"
                        :bottom-placeholders="bottomRows"
                        @scroll="setScrollPos"
                    >
                        <template v-slot="{ item, index }">
                            <CollectionContentItem :item="item" :index="index" />
                        </template>
                    </VirtualScroller>
                </template>
            </Layout>
        </CollectionContentProvider>
    </DscProvider>
</template>

<script>
import { History } from "../model";
import { updateContentFields } from "../model/queries";
import { cacheContent } from "../caching";

import { DscProvider, CollectionContentProvider } from "../providers";
import Layout from "../Layout";
import TopNav from "./TopNav";
import Details from "./Details";
import ListMixin from "../ListMixin";
import VirtualScroller from "../../VirtualScroller";
import { CollectionContentItem } from "../ContentItem";

export default {
    mixins: [ListMixin],
    components: {
        DscProvider,
        CollectionContentProvider,
        Layout,
        TopNav,
        Details,
        VirtualScroller,
        CollectionContentItem,
    },
    props: {
        history: { type: History, required: true },
        selectedCollections: { type: Array, required: true },
    },
    data: () => ({
        showTags: false,
        showFilter: false,
    }),
    computed: {
        selectedCollection() {
            const arr = this.selectedCollections;
            const selected = arr[arr.length - 1];
            return selected;
        },
        isRoot() {
            return this.selectedCollection == this.selectedCollections[0];
        },
        writable() {
            return this.isRoot;
        },
    },
    methods: {
        // change the data of the root collection, anything past the root
        // collection is part of the dataset collection, which i believe is supposed to
        // be immutable, so only edit name, tags, blah of top-level selected collection,

        async updateDsc(collection, fields) {
            // console.log("updateDsc", this.writable, collection, fields);
            if (this.writable) {
                const ajaxResult = await updateContentFields(collection, fields);
                await cacheContent({ ...collection, ...ajaxResult });
            }
        },
    },
};
</script>
