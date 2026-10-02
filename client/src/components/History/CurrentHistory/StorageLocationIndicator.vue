<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { HistorySummary } from "@/api";
import { useSync } from "@/composables/sync";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { useUserStore } from "@/stores/userStore";

import SelectPreferredStore from "./SelectPreferredStore.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

const props = defineProps<{
    history: HistorySummary;
}>();

const preferredObjectStoreId = ref<string | null>(null);

useSync(() => props.history.preferred_object_store_id, preferredObjectStoreId);

const objectStoreStore = useObjectStoreStore();

const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const userPreferredObjectStoreId = computed(() => {
    const user = currentUser.value;
    if (user && "preferred_object_store_id" in user) {
        return user.preferred_object_store_id ?? null;
    } else {
        return null;
    }
});

function onUpdatePreferredObjectStoreId(id: string | null) {
    preferredObjectStoreId.value = id;
}

const showSelectPreferredStore = ref(false);

const storageLocationButtonTitle = computed(() => {
    if (!isAnonymous.value) {
        return "View and select storage location";
    } else {
        return "Log in to view and select storage location";
    }
});
</script>

<template>
    <div class="storage-location-indicator">
        <GLink
            tooltip
            thin
            class="storage-location-link"
            :title="storageLocationButtonTitle"
            :disabled="isAnonymous"
            @click="showSelectPreferredStore = !showSelectPreferredStore">
            <FontAwesomeIcon :icon="faHdd" />
            {{ objectStoreStore.getObjectStoreNameById(preferredObjectStoreId) ?? "Default Storage" }}
        </GLink>

        <SelectPreferredStore
            :show.sync="showSelectPreferredStore"
            show-sub-setting
            :user-preferred-object-store-id="userPreferredObjectStoreId"
            :preferred-object-store-id="preferredObjectStoreId"
            :history="history"
            @updated="onUpdatePreferredObjectStoreId" />
    </div>
</template>

<style lang="scss" scoped>
.storage-location-indicator {
    margin: 0.5rem 0;

    .storage-location-link {
        &:hover,
        &:focus {
            text-decoration: none;
        }
    }
}
</style>
