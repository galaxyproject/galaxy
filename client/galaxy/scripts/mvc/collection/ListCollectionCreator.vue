<template> 
        <div>
          <v-on:click.more-help=_clickMoreHelp>
          <v-on:click.less-help=_clickLessHelp>
          <v-on:click.main-help=_toggleHelp>
          <v-on:click.header.alert button=_hideAlert>
          <v-on:click.collection-elements=clearSelectedElements>
          <v-on:click.reset=reset>
          <v-on:click.clear-selected=clearSelectedElements>
          <v-on:click.cancel-create=_cancelCreate>
          <v-on:click.create-collection=_clickCreate>
          <v-on:dragover.collection-elements=_dravoverElements>
          <v-on:drop.collection-elements=_dropElements>
          <v-on:collection-element.dragstart .collection-elements=_elementDragstart>
          <v-on:collection-element.dragend . collection-elements=_elementDragend>
          <v-on:change.collection-name=_changeName>
          <v-on:keydown.collection-name=_nameCheckForEnter>
          <v-on:change.hide-originals=_changeHideOriginals>
        </div>
</template>

<script>
import HDCA from "mvc/history/hdca-model";
import CollectionCreatorMixin from "mvc/collection/mixins/CollectionCreatorMixin";

import "ui/hoverhighlight";
export default {
    data: { function () {
        return {
            minElements: 1,
            _logNamespace: "collections",
            elementViewClass: DatasetCollectionElementView,
            collectionClass: HDCA.HistoryDatasetCollection,
            className: "list-collection-creator collection-creator flex-row-container",
            footerSettings: {
                ".hide-originals": "hideOriginals",
            },
        }
    }
    },
    props: {
        attributes,    
    },
    computed: {
    },
    methods: {
        /** set up instance vars */
        _instanceSetUp: function () {
            /** Ids of elements that have been selected by the user - to preserve over renders */
            this.selectedIds = {};
            /** DOM elements currently being dragged */
            this.$dragging = null;
            /** Used for blocking UI events during ajax/operations (don't post twice) */
            this.blocking = false;
        },
    },
    created: {
        /** set up initial options, instance vars, behaviors */
        initialize: function ( ) {
            this.metric("ListCollectionCreator.initialize", attributes);
            var creator = this;

            _.each(this.defaultAttributes, (value, key) => {
                value = attributes[key] || value;
                creator[key] = value;
            });

            /** unordered, original list - cache to allow reversal */
            creator.initialElements = attributes.elements || [];

            this._setUpCommonSettings(attributes);
            this._instanceSetUp();
            this._elementsSetUp();
            this._setUpBehaviors();
        },
    },
    watch: {},
    components: { CollectionCreatorMixin },
};
</script>
