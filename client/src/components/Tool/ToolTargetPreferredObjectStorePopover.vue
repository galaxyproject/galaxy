<template>
    <b-popover target="tool-storage" triggers="hover" placement="bottomleft" boundary="window">
        <template v-slot:title>{{ title }}</template>
        <div class="popover-wide">
            <p v-if="toolPreferredObjectStoreId">
                The {{ preferredOrEmptyString }} Galaxy storage has been set at the tool level, by default history or
                user preferences will be used and if those are not set Galaxy will pick an administrator-configured
                default.
            </p>
            <ShowSelectedObjectStore
                v-if="toolPreferredObjectStoreId"
                :preferred-object-store-id="toolPreferredObjectStoreId"
                for-what="Galaxy will default to storing this tool run's output in">
            </ShowSelectedObjectStore>
            <div v-else>
                No selection has been made for this tool execution. Defaults from history, user, or Galaxy will be used.
            </div>
            <div v-localize>
                Change {{ preferredOrEmptyString }} Galaxy storage by clicking on the storage button in the tool header.
            </div>
        </div>
    </b-popover>
</template>

<script>
import showTargetPopoverMixin from "components/ObjectStore/showTargetPopoverMixin";

export default {
    mixins: [showTargetPopoverMixin],
    props: {
        toolPreferredObjectStoreId: {
            type: String,
            default: null,
        },
        user: { type: Object, required: true },
    },
};
</script>
<style scoped lang="scss">
.popover-wide {
    max-width: 30rem;
}
</style>
