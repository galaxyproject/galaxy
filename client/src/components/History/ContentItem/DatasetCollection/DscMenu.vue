<template>
    <PriorityMenu>
        <b-dropdown no-caret right variant="link" size="sm" boundary="window" toggle-class="p-1 pl-3">
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
        <PriorityMenuItem
            v-if="hasJob"
            key="dataset-details"
            title="View Details"
            @click.stop.prevent="backboneRoute(path)"
            icon="fa fa-info-circle"
        />
    </PriorityMenu>
</template>
<script>
import { PriorityMenu, PriorityMenuItem } from "components/PriorityMenu";
import { DatasetCollection } from "../../model/DatasetCollection";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        PriorityMenu,
        PriorityMenuItem,
    },
    props: {
        dsc: { type: DatasetCollection, required: true },
    },
    computed: {
        hasJob() {
            return this.dsc?.job_source_type == "Job";
        },
        path() {
            return `jobs/${this.dsc.job_source_id}/view`;
        },
    },
};
</script>
