<template>
    <div>
        <div v-for="contentItem in collectionContents" :index="1" :key="contentItem.id">
            <DatasetProvider
                v-if="contentItem.element_type === 'hda'"
                :id="contentItem.object.id"
                v-slot="{
                    item,
                    loading,
                }"
            >
                <div>
                    <loading-span v-if="loading" message="Loading datasets" />
                    <DatasetUIWrapper
                       v-if="item"
                       :item="item"
                       :element_identifier="contentItem.element_identifier"
                       v-bind:index="1"
                       v-bind:showTags="true"
                       >
                    </DatasetUIWrapper>
                </div>
            </DatasetProvider>
            <DatasetCollectionUIWrapper
               v-if="contentItem.element_type === 'dataset_collection'"
               :item="contentItem"
               :element_count="collectionContents.length + 1"
               v-bind:index="1"
               v-bind:showTags="true"
               >
            </DatasetCollectionUIWrapper>
        </div>
    </div>
</template>
<script>
import {DatasetProvider} from "components/History/providers/DatasetProvider";
import DatasetUIWrapper from "components/History/ContentItem/Dataset/DatasetUIWrapper";

import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        DatasetProvider,
        DatasetCollectionUIWrapper: () => import("components/History/ContentItem/DatasetCollection/DatasetCollectionUIWrapper"),
        DatasetUIWrapper,
        LoadingSpan,
    },
    props: {
        collectionContents: {type: Array, required: true}
    },

}
</script>