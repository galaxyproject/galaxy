<script setup lang="ts">
import { faHourglass } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { parseISO } from "date-fns";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { HDASummary, HDCASummary } from "@/api";
import { isHDA } from "@/api";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

interface ExpirableObjectStoreTime {
    objectStoreId: string;
    objectExpiresAfterDays: number;
    objectStoreName: string;
    oldestCreateTime: Date;
}

const props = defineProps<{
    item: HDASummary | HDCASummary;
}>();

const store = useObjectStoreStore();
const { selectableObjectStores } = storeToRefs(store);

const defaultName = "Unnamed Object Store";

const expirableObjectStoreTime = computed<ExpirableObjectStoreTime | undefined>(() => {
    const item = props.item;
    if (isHDA(item)) {
        // Single object store case: check if it has an expiration policy
        const expirableObjectStore = selectableObjectStores.value?.find(
            (objectStore) =>
                objectStore.object_store_id === item.object_store_id &&
                (objectStore.object_expires_after_days ?? 0) > 0,
        );
        if (!expirableObjectStore) {
            return undefined;
        }
        return {
            objectStoreId: expirableObjectStore.object_store_id ?? "default",
            objectExpiresAfterDays: expirableObjectStore.object_expires_after_days ?? 0,
            objectStoreName: expirableObjectStore.name ?? defaultName,
            oldestCreateTime: parseISO(`${item.create_time}Z`),
        };
    } else if (item.store_times_summary !== undefined) {
        // Multiple object stores case: find the one with the shortest expiration date
        const expirableStoreTimes: ExpirableObjectStoreTime[] = (item.store_times_summary ?? [])
            .map((storeTime) => {
                const objectStore = selectableObjectStores.value?.find(
                    (os) => os.object_store_id === storeTime.object_store_id,
                );
                if (!objectStore || (objectStore.object_expires_after_days ?? 0) <= 0) {
                    return null;
                }
                return {
                    objectStoreId: storeTime.object_store_id,
                    objectExpiresAfterDays: objectStore.object_expires_after_days ?? 0,
                    objectStoreName: objectStore.name ?? defaultName,
                    oldestCreateTime: parseISO(`${storeTime.oldest_create_time}Z`),
                };
            })
            .filter((storeTime): storeTime is ExpirableObjectStoreTime => storeTime !== null);
        if (expirableStoreTimes.length === 0) {
            return undefined;
        }
        // Find the store with the shortest expiration time according to the oldest creation time and expiration days
        expirableStoreTimes.sort((a, b) => {
            const aExpiration = new Date(a.oldestCreateTime);
            aExpiration.setDate(aExpiration.getDate() + a.objectExpiresAfterDays);
            const bExpiration = new Date(b.oldestCreateTime);
            bExpiration.setDate(bExpiration.getDate() + b.objectExpiresAfterDays);
            return aExpiration.getTime() - bExpiration.getTime();
        });
        return expirableStoreTimes[0];
    }
    return undefined;
});

const objectStoreName = computed(() => {
    return expirableObjectStoreTime.value?.objectStoreName ?? defaultName;
});

const expirationDate = computed(() => {
    const target = expirableObjectStoreTime.value;
    if (!target) {
        return null;
    }
    // Calculate the expiration date based on the creation date and the expiration days of the object store
    const expirationDate = new Date(target.oldestCreateTime);
    expirationDate.setDate(expirationDate.getDate() + target.objectExpiresAfterDays);
    return expirationDate;
});

const timeToExpire = computed<number | null>(() => {
    if (!expirationDate.value) {
        return null;
    }
    // Calculate the difference in days between the expiration date and the current date
    return expirationDate.value.getTime() - new Date().getTime();
});

const canExpire = computed(() => timeToExpire.value !== null);

const daysToExpire = computed(() => {
    if (timeToExpire.value === null) {
        return null;
    }
    return timeToExpire.value < 0 ? 0 : Math.floor(timeToExpire.value / (1000 * 60 * 60 * 24));
});

const hasExpired = computed(() => {
    return expirationDate.value ? expirationDate.value < new Date() : false;
});

const expirationMessage = computed(() => {
    if (daysToExpire.value === null) {
        return undefined;
    }
    if (hasExpired.value) {
        return "Expired";
    }
    if (daysToExpire.value !== null && daysToExpire.value <= 1) {
        return `Expires soon!`;
    }
    return `Expires in ${daysToExpire.value} days`;
});

const expirationTooltip = computed(() => {
    const itemType = isHDA(props.item) ? "dataset" : "dataset collection (or any of its datasets)";
    if (!expirationDate.value) {
        return `This ${itemType} does not have an expiration date.`;
    }
    if (hasExpired.value) {
        return `This ${itemType} was stored in ${
            objectStoreName.value
        } and has expired on ${expirationDate.value.toDateString()}.`;
    }
    return `This ${itemType} is stored in ${
        objectStoreName.value
    } and expires on ${expirationDate.value.toDateString()}.`;
});

const variant = computed(() => {
    if (hasExpired.value) {
        return "danger";
    }
    if (daysToExpire.value && daysToExpire.value <= 5) {
        return "warning";
    }
    return "secondary";
});
</script>
<template>
    <span v-if="canExpire" class="expiration-indicator">
        <BBadge v-b-tooltip.noninteractive.hover.left :variant="variant" :title="expirationTooltip">
            <FontAwesomeIcon :icon="faHourglass" /> {{ expirationMessage }}
        </BBadge>
    </span>
</template>
