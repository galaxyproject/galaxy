<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faChevronLeft,
    faChevronRight,
    faExclamationCircle,
    faExclamationTriangle,
    faInfoCircle,
    faTimes,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { type components } from "@/api/schema";
import { useMarkdown } from "@/composables/markdown";
import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";
import { ensureDefined } from "@/utils/assertions";
import { match } from "@/utils/utils";

import Heading from "@/components/Common/Heading.vue";

library.add(faInfoCircle, faTimes, faChevronRight, faChevronLeft, faExclamationTriangle, faExclamationCircle);

type BroadcastNotificationCreateRequest = components["schemas"]["BroadcastNotificationCreateRequest"];

type Options =
    | {
          previewMode?: false;
          broadcasts: BroadcastNotification[];
      }
    | {
          previewMode: true;
          broadcast: BroadcastNotificationCreateRequest;
      };

const props = defineProps<{
    options: Options;
}>();

const broadcastsStore = useBroadcastsStore();
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const multiple = computed(() => {
    if (props.options.previewMode) {
        return false;
    } else {
        return props.options.broadcasts.length > 1;
    }
});

const page = ref(0);

const currentPage = computed({
    get: () => {
        return page.value;
    },
    set: (newPage) => {
        page.value = newPage;
        checkPageInBounds();
    },
});

function checkPageInBounds() {
    if (page.value < 0) {
        page.value = sortedBroadcasts.value.length - 1;
    } else if (page.value >= sortedBroadcasts.value.length) {
        page.value = 0;
    }
}

const displayedBroadcast = computed(
    () => ensureDefined(sortedBroadcasts.value[currentPage.value]) as BroadcastNotification
);

type Variant = BroadcastNotification["variant"];

function sortByImportanceAndPublicationTime(a: BroadcastNotification, b: BroadcastNotification) {
    const priority = (v: Variant) =>
        match(v, {
            info: () => 0,
            warning: () => 1,
            urgent: () => 2,
        });

    const priorityA = priority(a.variant);
    const priorityB = priority(b.variant);

    if (priorityA !== priorityB) {
        return priorityB - priorityA;
    } else {
        return new Date(b.publication_time).getTime() - new Date(a.publication_time).getTime();
    }
}

const sortedBroadcasts = computed(() => {
    if (props.options.previewMode) {
        return [props.options.broadcast];
    } else {
        const sorted = [...props.options.broadcasts];
        sorted.sort(sortByImportanceAndPublicationTime);
        return sorted;
    }
});

watch(
    () => sortedBroadcasts.value,
    () => {
        checkPageInBounds();
    }
);

function actionLinkBind(link: string) {
    if (link.startsWith("/")) {
        return {
            to: link,
        };
    } else {
        return {
            href: link,
        };
    }
}

function dismiss() {
    if (!props.options.previewMode) {
        broadcastsStore.dismissBroadcast(displayedBroadcast.value);
    }
}
</script>

<template>
    <div
        class="broadcast-container shadow"
        :class="{
            single: !multiple,
            preview: props.options.previewMode,
            warning: displayedBroadcast.variant === 'warning',
            urgent: displayedBroadcast.variant === 'urgent',
        }">
        <BButton
            v-if="multiple"
            class="arrow left inline-icon-button area-l"
            title="Previous"
            @click="currentPage -= 1">
            <FontAwesomeIcon fixed-width icon="fa-chevron-left" />
        </BButton>

        <div class="info-icon area-i">
            <FontAwesomeIcon
                v-if="displayedBroadcast.variant === 'warning'"
                class="warning"
                icon="fa-exclamation-triangle" />
            <FontAwesomeIcon
                v-if="displayedBroadcast.variant === 'urgent'"
                class="urgent"
                icon="fa-exclamation-circle" />
        </div>

        <section class="main-content area-m">
            <Heading h2>{{ displayedBroadcast.content.subject }}</Heading>
            <div class="message mb-1" v-html="renderMarkdown(displayedBroadcast.content.message)"></div>
            <div class="bottom-row">
                <div class="action-links">
                    <BButton
                        v-for="(actionLink, index) in displayedBroadcast.content.action_links"
                        :key="`${displayedBroadcast.id}-${index}`"
                        :variant="displayedBroadcast.variant === 'urgent' ? 'danger' : 'primary'"
                        v-bind="actionLinkBind(actionLink.link)">
                        {{ actionLink.action_name }}
                    </BButton>
                </div>

                <div v-if="multiple" class="page-indicator">{{ currentPage + 1 }} / {{ sortedBroadcasts.length }}</div>
            </div>
        </section>

        <BButton v-if="multiple" class="arrow right inline-icon-button area-r" title="Next" @click="currentPage += 1">
            <FontAwesomeIcon fixed-width icon="fa-chevron-right" />
        </BButton>

        <BButton class="dismiss-button inline-icon-button area-x" title="Dismiss" @click="dismiss">
            <FontAwesomeIcon fixed-width icon="fa-times" />
        </BButton>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

$margin: 1rem;

.broadcast-container {
    z-index: 999999;
    position: fixed;
    bottom: $margin;
    left: 50%;
    transform: translate(-50%, 0);
    height: 200px;
    width: min(calc(100% - $margin - $margin), 1200px);
    background: $white;
    border-color: $border-color;
    border-width: 1px;
    border-style: solid;
    border-radius: 0.5rem;
    display: grid;
    grid-template-columns: 50px 1fr 50px;
    grid-template-rows: 50px 1fr 50px;
    grid-template-areas:
        "i m x"
        "l m r"
        ". m .";

    .area-l {
        grid-area: l;
    }
    .area-m {
        grid-area: m;
    }
    .area-x {
        grid-area: x;
    }
    .area-r {
        grid-area: r;
    }
    .area-i {
        grid-area: i;
    }

    &.preview {
        position: relative;
        bottom: 0;
    }

    &.warning {
        border-color: $brand-warning;
    }

    &.urgent {
        border-color: $brand-danger;
        background: linear-gradient(to top, lighten($brand-warning, 35%), $white 120px);
    }

    .arrow {
        font-size: 2rem;

        &.left {
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
        }

        &.right {
            border-top-right-radius: 0;
            border-bottom-right-radius: 0;
        }
    }

    .dismiss-button {
        font-size: 1.5rem;
        color: $border-color;

        &:hover {
            background: none;
            color: $brand-danger;
        }

        &:focus {
            color: $brand-primary;
        }
    }

    .info-icon {
        display: grid;
        place-items: center;
        font-size: 1.5rem;

        .urgent {
            color: $brand-danger;
        }

        .warning {
            color: $brand-warning;
        }
    }

    .main-content {
        display: flex;
        flex-direction: column;
        height: 100%;
        padding: 0.75rem 0.25rem;

        .message {
            flex: 1;
            overflow-y: scroll;
        }

        .bottom-row {
            display: grid;
            grid-template-columns: 1fr auto 1fr;

            .action-links {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
            }

            .page-indicator {
                align-self: end;
                justify-self: center;
            }
        }
    }
}
</style>
