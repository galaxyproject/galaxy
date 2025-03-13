<template>
    <b-popover :target="target" triggers="hover" placement="bottomleft" boundary="window">
        <template v-slot:title>{{ title }}</template>
        <div class="popover-wide">
            <p v-if="invocationPreferredObjectStoreId">Galaxy Storage has been set at the invocation level.</p>
            <ShowSelectedObjectStore
                v-if="invocationPreferredObjectStoreId"
                :preferred-object-store-id="invocationPreferredObjectStoreId"
                for-what="Galaxy will default to storing this tool run's output in">
            </ShowSelectedObjectStore>
            <div v-else>
                No selection has been made for this workflow invocation. Defaults from history, user, or Galaxy will be
                used.
            </div>
            <div v-localize>
                Change {{ preferredOrEmptyString }} Galaxy storage by clicking on the storage button in the workflow
                run header.
            </div>
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

<style scoped lang="scss">
.popover-wide {
    max-width: 30rem;
}
</style>
