<template>
    <div class="collection-menu">
        <PriorityMenu :starting-height="27">
            <PriorityMenuItem
                v-if="notIn(STATES.DISCARDED)"
                key="edit-collection"
                class="collection-edit-view"
                :title="editButtonTitle"
                :disabled="collection.deleted || isIn(STATES.UPLOAD, STATES.NEW)"
                @click.stop="backboneRoute('collection/edit/' + collection.hdca_id)"
                icon="fa fa-pencil"
            />
            <PriorityMenuItem
                v-if="notIn(STATES.DISCARDED)"
                key="edit-collection"
                :title="deleteCollectionButtonTitle"
                @click.stop="$emit('delete')"
                icon="fas fa-trash"
            />
            <PriorityMenuItem
                v-if="notIn(STATES.DISCARDED)"
                key="edit-collection"
                :title="deleteDatasetsButtonTitle"
                @click.stop="$emit('delete', { recursive: true })"
                icon="fas fa-trash"
            />
            <PriorityMenuItem
                v-if="notIn(STATES.DISCARDED)"
                key="edit-collection"
                :title="purgeCollectionButtonTitle"
                @click.stop="$emit('delete', { recursive: true, purge: true })"
                icon="fas fa-trash"
            />
        </PriorityMenu>
    </div>
</template>

<script>
import { DatasetCollection } from "../../model";
import { PriorityMenu, PriorityMenuItem } from "components/PriorityMenu";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
export default {
    components: {
        PriorityMenu,
        PriorityMenuItem,
    },
    mixins: [legacyNavigationMixin],
    inject: ["STATES"],
    props: {
        collection: { type: DatasetCollection, required: true },
    },
    computed: {
        editButtonTitle() {
            if (this.collection.deleted) {
                return "Collection must not be deleted to edit";
            }
            if (this.collection.purged) {
                return "Cannot edit attributes of collections removed from disk";
            }
            const unreadyStates = new Set([this.STATES.UPLOAD, this.STATES.NEW]);
            if (unreadyStates.has(this.collection.state)) {
                return "This collection is not yet editable";
            }
            return "Edit attributes";
        },
        deleteCollectionButtonTitle() {
            return "Delete Collection Only";
        },
        deleteDatasetsButtonTitle() {
            return "Delete Contained Datasets";
        },
        purgeCollectionButtonTitle() {
            return "Purge Contained Datasets";
        },
    },
    methods: {
        collectionEditURL: function () {
            return "/collection/edit/" + this.collection.hdca_id;
        },
        notIn(...states) {
            const badStates = new Set(states);
            return !badStates.has(this.collection.state);
        },
        isIn(...states) {
            const goodStates = new Set(states);
            return goodStates.has(this.collection.state);
        },
    },
};
</script>
