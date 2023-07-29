<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useMarkdown } from "@/composables/markdown";
import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";

import Heading from "@/components/Common/Heading.vue";

library.add(faInfoCircle, faTimes);

const router = useRouter();

const broadcastsStore = useBroadcastsStore();
const { activeBroadcasts } = storeToRefs(useBroadcastsStore());
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const currentBroadcast = computed(() => getNextActiveBroadcast());

const remainingBroadcastsCountText = computed(() => {
    const count = activeBroadcasts.value.length - 1;
    return count > 0 ? `${count} more` : "";
});

function getNextActiveBroadcast(): BroadcastNotification | undefined {
    return activeBroadcasts.value.sort(sortByPublicationTime).at(0);
}

function sortByPublicationTime(a: BroadcastNotification, b: BroadcastNotification) {
    return new Date(a.publication_time).getTime() - new Date(b.publication_time).getTime();
}

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
    onDismiss(item);
}

function onDismiss(item: BroadcastNotification) {
    broadcastsStore.dismissBroadcast(item);
}
</script>

<template>
    <div v-if="currentBroadcast">
        <BRow
            align-v="center"
            class="broadcast-banner m-0"
            :class="{ 'non-urgent': currentBroadcast.variant !== 'urgent' }">
            <BCol cols="auto">
                <FontAwesomeIcon
                    class="mx-2"
                    size="2xl"
                    :class="`text-${getBroadcastVariant(currentBroadcast)}`"
                    :icon="faInfoCircle" />
            </BCol>
            <BCol>
                <BRow align-v="center">
                    <Heading size="md" bold>
                        {{ currentBroadcast.content.subject }}
                    </Heading>
                </BRow>
                <BRow align-v="center">
                    <span class="broadcast-message" v-html="renderMarkdown(currentBroadcast.content.message)" />
                </BRow>
                <BRow>
                    <div v-if="currentBroadcast.content.action_links">
                        <BButton
                            v-for="actionLink in currentBroadcast.content.action_links"
                            :key="actionLink.action_name"
                            :title="actionLink.action_name"
                            variant="primary"
                            @click="onActionClick(currentBroadcast, actionLink.link)">
                            {{ actionLink.action_name }}
                        </BButton>
                    </div>
                </BRow>
            </BCol>
            <BCol cols="auto" align-self="center" class="p-0">
                <BButton
                    id="dismiss-button"
                    variant="light"
                    class="align-items-center d-flex"
                    @click="onDismiss(currentBroadcast)">
                    <FontAwesomeIcon class="mx-1" icon="times" />
                    Dismiss
                </BButton>
                <div v-if="remainingBroadcastsCountText" class="text-center mt-2">
                    {{ remainingBroadcastsCountText }}...
                </div>
            </BCol>
        </BRow>
    </div>
</template>

<style lang="scss" scoped>
.broadcast-banner {
    width: 100%;
    color: white;
    display: flex;
    z-index: 9999;
    padding: 1rem;
    position: fixed;
    min-height: 6rem;
    backdrop-filter: blur(0.2rem);
    justify-content: space-between;
    background-color: rgb(0, 0, 0, 0.7);
    box-shadow: 0 0 1rem 0 rgba(0, 0, 0, 0.5);

    .broadcast-message {
        font-size: large;
    }
}

.non-urgent {
    bottom: 0;
}
</style>
