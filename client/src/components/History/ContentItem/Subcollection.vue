<!-- a separate collection content item for collections inside of other collections -->

<template>
    <div
        v-bind="$attrs"
        v-on="$listeners"
        class="collapsed"
        :data-state="state"
        @keydown.arrow-right.self.stop.prevent="$emit('selectCollection')"
        @click.stop="$emit('selectCollection')"
    >
        <nav class="content-top-menu d-flex align-items-center justify-content-between p-1">
            <h5 class="flex-grow-1 overflow-hidden mr-auto text-nowrap text-truncate">
                <span class="name">{{ dsc.name }}</span>
                <span class="description">
                    ({{ dsc.collectionType | localize }} {{ dsc.collectionCountDescription | localize }})
                </span>
            </h5>
        </nav>
    </div>
</template>

<script>
import { DatasetCollection } from "../model/DatasetCollection";
import { STATES } from "../model";

export default {
    props: {
        item: { type: Object, required: true },
        index: { type: Number, required: true },
    },
    computed: {
        dsc() {
            return new DatasetCollection(this.item);
        },
        state() {
            // TODO: see if there are situations where this rule won't work
            // subcollection doesn't have as much information as the collection
            // did, but it's probably ok
            return this.dsc.state || STATES.OK;
        },
    },
};
</script>
