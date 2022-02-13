<template>
    <div class="collection-menu">
        <b-button-group>
            <IconButton
                icon="info-circle"
                v-if="hasJob"
                key="dataset-details"
                title="View Dataset Collection Details"
                @click.stop.prevent="backboneRoute(collectionDetailsPath)"
                variant="link"
                class="px-1">
            </IconButton>
            <IconButton
                v-if="notIn(STATES.DISCARDED)"
                icon="pen"
                :title="editButtonTitle"
                :disabled="dsc.deleted || isIn(STATES.UPLOAD, STATES.NEW)"
                @click.stop="backboneRoute('collection/edit/' + dsc.hdca_id)"
                variant="link"
                class="px-1 dsc-edit-view" />
            <b-dropdown v-if="notIn(STATES.DISCARDED)" no-caret right variant="link" size="sm" boundary="window">
                <template v-slot:button-content>
                    <Icon icon="trash" variant="link" />
                    <span class="sr-only">Delete Collection</span>
                </template>

                <b-dropdown-item @click.stop="$emit('delete')">
                    <span v-localize>Delete Collection Only</span>
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
import { DatasetCollection, STATES } from "../../model";
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
    props: {
        dsc: { type: DatasetCollection, required: true },
    },
    computed: {
        editButtonTitle() {
            if (this.dsc.deleted) {
                return "Collection must not be deleted to edit";
            }
            if (this.dsc.purged) {
                return "Cannot edit attributes of collections removed from disk";
            }
            const unreadyStates = new Set([STATES.UPLOAD, STATES.NEW]);
            if (unreadyStates.has(this.dsc.state)) {
                return "This collection is not yet editable";
            }
            return "Edit attributes";
        },
        deleteCollectionButtonTitle() {
            return "Delete Collection";
        },
        hasJob() {
            return this.dsc?.job_source_type == "Job";
        },
        collectionDetailsPath() {
            return `jobs/${this.dsc.job_source_id}/view`;
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
        notIn(...states) {
            const badStates = new Set(states);
            return !badStates.has(this.dsc.state);
        },
        isIn(...states) {
            const goodStates = new Set(states);
            return goodStates.has(this.dsc.state);
        },
    },
};
</script>
