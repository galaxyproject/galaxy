<script setup lang="ts">
import { storeToRefs } from "pinia";
import { BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";
import { library } from "@fortawesome/fontawesome-svg-core";
import { useBroadcastsStore, type BroadcastNotification } from "@/stores/broadcastsStore";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faInfoCircle, faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faInfoCircle, faTimes);

const router = useRouter();

const broadcastsStore = useBroadcastsStore();
const { activeBroadcasts } = storeToRefs(useBroadcastsStore());

function getBroadcastVariant(item: BroadcastNotification) {
    switch (item.variant) {
        case "urgent":
            return "danger";
        default:
            return item.variant;
    }
}

function onActionClick(item: BroadcastNotification, link: string) {
    if (link.startsWith("/")) {
        router.push(link);
    } else {
        window.open(link, "_blank");
    }
    broadcastsStore.dismissBroadcast(item);
}
</script>

<template>
    <div v-if="activeBroadcasts.length > 0">
        <div
            v-for="broadcast in activeBroadcasts"
            :key="broadcast.id"
            :class="{ 'urgent-broadcast': broadcast.variant === 'urgent' }">
            <div class="broadcast-banner">
                <FontAwesomeIcon
                    class="mx-2"
                    fade
                    size="2xl"
                    :class="`text-${getBroadcastVariant(broadcast)}`"
                    :icon="faInfoCircle" />
                <div class="d-flex align-items-center">
                    <span>
                        {{ broadcast.content.message }}
                    </span>
                    <div v-if="broadcast.content.action_links">
                        <BButton
                            v-for="actionLink in broadcast.content.action_links"
                            :key="actionLink.action_name"
                            class="mx-2"
                            :title="actionLink.action_name"
                            variant="primary"
                            @click="onActionClick(broadcast, actionLink.link)">
                            {{ actionLink.action_name }}
                        </BButton>
                    </div>
                </div>
                <BButton variant="light" title="Close" @click="broadcastsStore.dismissBroadcast(broadcast)">
                    <FontAwesomeIcon icon="times" />
                </BButton>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.urgent-broadcast {
    width: 100%;
    height: 100%;
    z-index: 1000;
    position: fixed;
    background-color: rgb(0, 0, 0, 0.6);
}
.broadcast-banner {
    bottom: 0;
    width: 100%;
    height: 6rem;
    color: white;
    display: flex;
    z-index: 9999;
    padding: 0 1rem;
    position: fixed;
    align-items: center;
    backdrop-filter: blur(0.2rem);
    justify-content: space-between;
    background-color: rgb(0, 0, 0, 0.7);
    box-shadow: 0 0 1rem 0 rgba(0, 0, 0, 0.5);
}
</style>
