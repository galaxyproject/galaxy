<template>
    <b-popover :target="target" triggers="hover" placement="bottomleft">
        <template v-slot:title>{{ title }}</template>
        <p v-if="invocationPreferredObjectStoreId">This target object store has been set at the invocation level.</p>
        <ShowSelectedObjectStore
            v-if="invocationPreferredObjectStoreId"
            :preferred-object-store-id="invocationPreferredObjectStoreId"
            for-what="Galaxy will default to storing this tool run's output in">
        </ShowSelectedObjectStore>
        <div v-else>
            No selection has been made for this worklfow invocation. Defaults from history, user, or Galaxy will be
            used.
        </div>
        <div v-localize>
            Change this preference object store target by clicking on the storage button in the worklfow run header.
        </div>
    </b-popover>
</template>

<script>
import showTargetPopoverMixin from "components/ObjectStore/showTargetPopoverMixin";

export default {
    mixins: [showTargetPopoverMixin],
    props: {
        invocationPreferredObjectStoreId: {
            type: String,
            default: null,
        },
        target: {
            type: String,
            required: true,
        },
    },
};
</script>
