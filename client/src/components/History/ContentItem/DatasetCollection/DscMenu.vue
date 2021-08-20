<template>
    <div class="collection-menu">
        <b-button-group>
            <IconButton
                v-if="notIn(STATES.DISCARDED)"
                icon="pen"
                :title="editButtonTitle"
                :disabled="collection.deleted || isIn(STATES.UPLOAD, STATES.NEW)"
                @click.stop="backboneRoute('collection/edit/' + collection.hdca_id)"
                variant="link"
                class="px-1 collection-edit-view"
            />
            <b-dropdown v-if="notIn(STATES.DISCARDED)" no-caret right variant="link" size="sm" boundary="window">
                <template v-slot:button-content>
                    <Icon icon="trash" variant="link" />
                    <span class="sr-only">Delete Collection</span>
                </template>

                <b-dropdown-item @click.stop="$emit('delete')">
                    <span v-localize>Delete Collection Only </span>
                </b-dropdown-item>

                <b-dropdown-item @click.stop="$emit('delete', { recursive: true })">
                    <span v-localize>Delete Contained Datasets</span>
                </b-dropdown-item>

                <b-dropdown-item @click.stop="$emit('delete', { recursive: true, purge: true })">
                    <span v-localize>Purge Contained Datasets</span>
                </b-dropdown-item>
            </b-dropdown>
        </b-button-group>
    </div>
</template>

<script>
import { DatasetCollection } from "../../model";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import IconButton from "components/IconButton";

Vue.use(BootstrapVue);
export default {
    data() {
        return {
            deleteSelected: null,
            deleteCollectionModalShow: false,
        };
    },
    components: {
        IconButton,
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
            return "Delete Collection";
        },
    },
    methods: {
        runDelete: function (kind) {
            if (kind) {
                this.$emit("delete", kind);
            } else {
                this.$emit("delete");
            }
        },
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
