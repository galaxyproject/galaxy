<template>
    <PriorityMenu :starting-height="27">
        <PriorityMenuItem>
            <b-dropdown no-caret right variant="link" size="sm" boundary="window" toggle-class="p-1">
                <template v-slot:button-content>
                    <i class="fas fa-trash" />
                    <span class="sr-only">Delete Collection</span>
                </template>

                <b-dropdown-item @click.stop="$emit('deleteCollection')"> Delete Collection Only </b-dropdown-item>

                <b-dropdown-item @click.stop="$emit('deleteCollection', { recursive: true })">
                    Delete Contained Datasets
                </b-dropdown-item>

                <b-dropdown-item @click.stop="$emit('deleteCollection', { recursive: true, purge: true })">
                    Purge Contained Datasets
                </b-dropdown-item>
            </b-dropdown>
        </PriorityMenuItem>
        <PriorityMenuItem
            v-if="notIn(STATES.DISCARDED)"
            key="edit-collection"
            :title="editButtonTitle"
            :disabled="collection.deleted || isIn(STATES.UPLOAD, STATES.NEW)"
            @click.stop="backboneRoute('collection/edit/' + collection.hdca_id)"
            icon="fa fa-pencil"
        />
    </PriorityMenu>
</template>

<script>
import { DatasetCollection } from "../../model";
import { PriorityMenu, PriorityMenuItem } from "components/PriorityMenu";
import { legacyNavigationMixin } from "components/plugins";
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
                return "Undelete collection to edit attributes";
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
