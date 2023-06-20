<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { PropType } from "vue";
import { useRouter } from "vue-router/composables";

import { useMarkdown } from "@/composables/markdown";
import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";

import Heading from "@/components/Common/Heading.vue";

library.add(faInfoCircle, faTimes);

const props = defineProps({
    broadcast: {
        type: Object as PropType<BroadcastNotification>,
        required: true,
    },
    previewMode: {
        type: Boolean,
        default: false,
    },
});

const router = useRouter();
const broadcastsStore = useBroadcastsStore();
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
    props.previewMode && broadcastsStore.dismissBroadcast(item);
}
</script>

<template>
    <BRow
        align-v="center"
        class="broadcast-banner m-0"
        :class="{ 'non-urgent': broadcast.variant !== 'urgent', 'fixed-position': !previewMode }">
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
                <BButton
                    v-for="actionLink in broadcast.content.action_links"
                    :key="actionLink.action_name"
                    class="mx-1"
                    :title="actionLink.action_name"
                    variant="primary"
                    @click="onActionClick(broadcast, actionLink.link)">
                    {{ actionLink.action_name }}
                </BButton>
            </BRow>
        </BCol>
        <BCol v-if="!previewMode" cols="auto" align-self="center" class="p-0">
            <BButton
                variant="light"
                class="align-items-center d-flex"
                @click="broadcastsStore.dismissBroadcast(broadcast)">
                <FontAwesomeIcon class="mx-1" icon="times" />
                Dismiss
            </BButton>
        </BCol>
    </BRow>
</template>

<style lang="scss" scoped>
.broadcast-banner {
    width: 100%;
    color: white;
    display: flex;
    z-index: 9999;
    padding: 1rem;
    min-height: 6rem;
    backdrop-filter: blur(0.2rem);
    justify-content: space-between;
    background-color: rgb(0, 0, 0, 0.7);
    box-shadow: 0 0 1rem 0 rgba(0, 0, 0, 0.5);

    .broadcast-message {
        font-size: large;
    }
}

.fixed-position {
    position: fixed;
}

.non-urgent {
    bottom: 0;
}
</style>
