<script setup lang="ts">
import { BPopover } from "bootstrap-vue";
import { computed } from "vue";

import { useStorageLocationConfiguration } from "@/composables/storageLocation";

import ShowSelectedObjectStore from "@/components/ObjectStore/ShowSelectedObjectStore.vue";

const { isOnlyPreference } = useStorageLocationConfiguration();

interface Props {
    historyId: string;
    historyPreferredObjectStoreId?: string;
    user: { preferred_object_store_id?: string | null };
}

const props = defineProps<Props>();

const preferredObjectStoreId = computed(() => {
    let id = props.historyPreferredObjectStoreId;
    if (!id) {
        id = props.user.preferred_object_store_id ?? undefined;
    }
    return id;
});

const title = computed(() => {
    if (isOnlyPreference.value) {
        return "Preferred Storage";
    } else {
        return "Storage";
    }
});
</script>

<template>
    <BPopover :target="`history-storage-${historyId}`" triggers="hover" placement="bottomleft" boundary="window">
        <template v-slot:title>{{ title }}</template>
        <div class="popover-wide">
            <p>
                <b
                    >This option only affects new datasets created in this history. Existing history datasets will
                    remain at their current storage.</b
                >
            </p>

            <p v-if="historyPreferredObjectStoreId" class="history-preferred-object-store-inherited">
                This storage has been set at the history level.
            </p>
            <p v-else class="history-preferred-object-store-not-inherited">
                This storage has been inherited from your user preferences (set in
                <router-link to="/user">User -> Preferences</router-link> -> {{ title }}). If that option is updated,
                this history will target that new default.
            </p>

            <ShowSelectedObjectStore
                v-if="preferredObjectStoreId"
                :preferred-object-store-id="preferredObjectStoreId"
                for-what="Galaxy will default to storing this history's datasets in " />
        </div>
    </BPopover>
</template>
<style scoped lang="scss">
.popover-wide {
    max-width: 30rem;
}
</style>
