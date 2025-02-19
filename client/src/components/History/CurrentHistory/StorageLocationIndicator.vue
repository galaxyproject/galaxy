<script setup lang="ts">
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { ref } from "vue";

import type { HistorySummary } from "@/api";
import { useSync } from "@/composables/sync";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

const props = defineProps<{
    history: HistorySummary;
}>();

const preferredObjectStoreId = ref(null);
useSync(() => props.history.preferred_object_store_id, preferredObjectStoreId);

const objectStoreStore = useObjectStoreStore();
objectStoreStore.fetchObjectStores();
</script>

<template>
    <div class="storage-location-indicator">
        <BButton class="ui-link">
            <FontAwesomeIcon :icon="faHdd" />
            {{ objectStoreStore.getObjectStoreNameById(preferredObjectStoreId) ?? "Default Storage" }}
        </BButton>
    </div>
</template>

<style lang="scss" scoped>
.storage-location-indicator {
}
</style>
