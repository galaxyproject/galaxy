<template>
    <b-button-group>
        <IconButton
            icon="info-circle"
            v-if="hasJob"
            key="dataset-details"
            title="View Dataset Collection Details"
            @click.stop.prevent="backboneRoute(collectionDetailsPath)"
            variant="link"
            class="px-1"
        >
        </IconButton>
        <b-dropdown right no-caret variant="link" size="sm" boundary="window" toggle-class="p-0">
            <template v-slot:button-content>
                <IconButton icon="trash" title="Delete Colletion" variant="link" class="px-1" />
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
</template>
<script>
import { DatasetCollection } from "../../model/DatasetCollection";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import IconButton from "components/IconButton";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        IconButton,
    },
    props: {
        dsc: { type: DatasetCollection, required: true },
    },
    computed: {
        hasJob() {
            return this.dsc?.job_source_type == "Job";
        },
        collectionDetailsPath() {
            return `jobs/${this.dsc.job_source_id}/view`;
        },
    },
};
</script>
