<template>
    <b-popover :target="`history-storage-${historyId}`" triggers="hover" placement="bottomleft">
        <template v-slot:title>Preferred Target Object Store</template>
        <p v-if="historyPreferredObjectStoreId" class="history-preferred-object-store-inherited">
            This target object store has been set at the history level.
        </p>
        <p v-else class="history-preferred-object-store-not-inherited">
            This target object store has been inherited from your user preferences (set in User -> Preferences ->
            Preferred Object Store). If that option is updated, this history will target that new default.
        </p>
        <ShowSelectedObjectStore
            v-if="preferredObjectStoreId"
            :preferred-object-store-id="preferredObjectStoreId"
            for-what="Galaxy will default to storing this history's datasets in "></ShowSelectedObjectStore>
        <div v-localize>
            Change this preference object store target by clicking on the storage button in the history panel.
        </div>
    </b-popover>
</template>

<script>
import ShowSelectedObjectStore from "components/ObjectStore/ShowSelectedObjectStore";

export default {
    components: {
        ShowSelectedObjectStore,
    },
    props: {
        historyId: {
            type: String,
            required: true,
        },
        historyPreferredObjectStoreId: {
            type: String,
            default: null,
        },
        user: { type: Object, required: true },
    },
    computed: {
        preferredObjectStoreId() {
            let id = this.historyPreferredObjectStoreId;
            if (!id) {
                id = this.user.preferred_object_store_id;
            }
            return id;
        },
    },
};
</script>
