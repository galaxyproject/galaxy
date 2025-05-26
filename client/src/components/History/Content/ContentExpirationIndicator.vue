<script setup lang="ts">
import { faHourglass } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { parseISO } from "date-fns";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useObjectStoreStore } from "@/stores/objectStoreStore";

interface ExpirableItem {
    id: string;
    create_time: string;
    object_store_id?: string | null;
    object_store_ids?: string[] | null;
}

const props = defineProps<{
    item: ExpirableItem;
}>();

const store = useObjectStoreStore();
const { selectableObjectStores } = storeToRefs(store);

const itemCreationDate = computed(() => parseISO(`${props.item.create_time}Z`));

const shortTermObjectStore = computed(() => {
    console.debug("Checking for short-term object store", props.item.object_store_id, props.item);
    if (props.item.object_store_id !== undefined) {
        // Single object store case: check if it has an expiration policy
        return selectableObjectStores.value?.find((objectStore) => {
            return (
                objectStore.object_store_id === props.item.object_store_id &&
                objectStore.object_expires_after_days !== undefined
            );
        });
    } else if (props.item.object_store_ids !== undefined) {
        // Multiple object stores case: find the one with the shortest expiration policy
        return selectableObjectStores.value
            ?.filter((objectStore) => {
                return (
                    objectStore.object_store_id &&
                    objectStore.object_expires_after_days !== undefined &&
                    props.item.object_store_ids?.includes(objectStore.object_store_id)
                );
            })
            .reduce((prev, curr) => {
                return (prev.object_expires_after_days ?? 0) < (curr.object_expires_after_days ?? 0) ? prev : curr;
            });
    }
    return undefined;
});

const objectStoreName = computed(() => {
    return shortTermObjectStore.value?.name ?? "Unknown";
});

const timeToExpire = computed<number | null>(() => {
    const targetObjectStore = shortTermObjectStore.value;
    if (!targetObjectStore || !targetObjectStore.object_expires_after_days) {
        return null;
    }
    // Calculate the expiration date based on the creation date and the expiration days of the object store
    const expirationDate = new Date(itemCreationDate.value);
    expirationDate.setDate(expirationDate.getDate() + targetObjectStore.object_expires_after_days);
    // Calculate the difference in days between the expiration date and the current date
    return expirationDate.getTime() - new Date().getTime();
});

const canExpire = computed(() => timeToExpire.value !== null);

const daysToExpire = computed(() => {
    if (timeToExpire.value === null) {
        return null;
    }
    return timeToExpire.value < 0 ? 0 : Math.floor(timeToExpire.value / (1000 * 60 * 60 * 24));
});

const isExpired = computed(() => {
    return daysToExpire.value === 0;
});

const expirationMessage = computed(() => {
    if (daysToExpire.value === null) {
        return undefined;
    }
    if (isExpired.value) {
        return "Expired";
    }
    if (daysToExpire.value !== null && daysToExpire.value <= 1) {
        return `Expires soon!`;
    }
    return `Expires in ${daysToExpire.value} days`;
});

const expirationTooltip = computed(() => {
    if (isExpired.value) {
        return `This dataset was stored in ${
            objectStoreName.value
        } and has expired on ${itemCreationDate.value.toDateString()}.`;
    }
    return `This dataset is stored in ${
        objectStoreName.value
    } and expires on ${itemCreationDate.value.toDateString()}.`;
});

const variant = computed(() => {
    if (isExpired.value) {
        return "danger";
    }
    if (daysToExpire.value && daysToExpire.value <= 5) {
        return "warning";
    }
    return "secondary";
});
</script>
<template>
    <span v-if="canExpire">
        <BBadge v-b-tooltip.noninteractive.hover.left :variant="variant" :title="expirationTooltip">
            <FontAwesomeIcon :icon="faHourglass" /> {{ expirationMessage }}
        </BBadge>
    </span>
</template>
