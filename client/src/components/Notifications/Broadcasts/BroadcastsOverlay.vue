<script setup lang="ts">
import { storeToRefs } from "pinia";
import { BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faInfoCircle, faTimes } from "@fortawesome/free-solid-svg-icons";

import Heading from "@/components/Common/Heading.vue";
import { useMarkdown } from "@/composables/markdown";
import { useBroadcastsStore, type BroadcastNotification } from "@/stores/broadcastsStore";

library.add(faInfoCircle, faTimes);

const router = useRouter();

const broadcastsStore = useBroadcastsStore();
const { activeBroadcasts } = storeToRefs(useBroadcastsStore());
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

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
        <div v-for="broadcast in activeBroadcasts" :key="broadcast.id">
            <BRow
                align-v="center"
                class="broadcast-banner m-0"
                :class="{ 'non-urgent': broadcast.variant !== 'urgent' }">
                <BCol cols="auto">
                    <FontAwesomeIcon
                        class="mx-2"
                        fade
                        size="2xl"
                        :class="`text-${getBroadcastVariant(broadcast)}`"
                        :icon="faInfoCircle" />
                </BCol>
                <BCol>
                    <BRow align-v="center">
                        <Heading size="md" bold>
                            {{ broadcast.content.subject }}
                        </Heading>
                    </BRow>
                    <BRow align-v="center">
                        <span class="broadcast-message" v-html="renderMarkdown(broadcast.content.message)" />
                    </BRow>
                    <BRow>
                        <div v-if="broadcast.content.action_links">
                            <BButton
                                v-for="actionLink in broadcast.content.action_links"
                                :key="actionLink.action_name"
                                :title="actionLink.action_name"
                                variant="primary"
                                @click="onActionClick(broadcast, actionLink.link)">
                                {{ actionLink.action_name }}
                            </BButton>
                        </div>
                    </BRow>
                </BCol>
                <BCol cols="auto" align-self="center" class="p-0">
                    <BButton
                        variant="light"
                        class="align-items-center d-flex"
                        @click="broadcastsStore.dismissBroadcast(broadcast)">
                        <FontAwesomeIcon class="mx-1" icon="times" />
                        Dismiss
                    </BButton>
                </BCol>
            </BRow>
        </div>
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
