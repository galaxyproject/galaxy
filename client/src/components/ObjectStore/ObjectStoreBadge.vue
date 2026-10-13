<script setup lang="ts">
import { escape } from "lodash";
import { computed, ref } from "vue";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";
import { MESSAGES } from "@/components/ObjectStore/badgeMessages";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

import GPopover from "@/components/BaseComponents/GPopover.vue";
import ConfigurationMarkdown from "@/components/ObjectStore/ConfigurationMarkdown.vue";
import ObjectStoreBadgeIcon from "@/components/ObjectStore/ObjectStoreBadgeIcon.vue";

interface Props {
    badge: ObjectStoreBadgeType;
    size?: string;
    /** An admin message opens a popover whose links can be reached; turn off inside dropdown options and popovers */
    interactive?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    size: "lg",
    interactive: true,
});

const trigger = ref<HTMLElement>();

const stockMessage = computed(() => {
    return MESSAGES[props.badge.type];
});

const message = computed<string>(() => {
    return props.badge.message || "";
});

// Otherwise a plain tooltip: no Tab stop, and it closes when the pointer leaves the badge.
const hasPopover = computed(() => props.interactive && !!message.value);

const tooltip = computed(() => {
    return `<p>${escape(stockMessage.value)}</p>` + (message.value ? markup(message.value, true) : "");
});
</script>

<template>
    <button v-if="hasPopover" ref="trigger" type="button" :aria-label="stockMessage" class="object-store-badge-wrapper">
        <ObjectStoreBadgeIcon :badge-type="badge.type" :size="size" />
    </button>
    <span v-else v-g-tooltip.hover.html="tooltip" role="img" class="object-store-badge-wrapper">
        <ObjectStoreBadgeIcon :badge-type="badge.type" :size="size" />
    </span>
    <GPopover
        v-if="hasPopover"
        :target="() => trigger"
        interactive
        :aria-label="stockMessage"
        triggers="hover"
        placement="top">
        <p>{{ stockMessage }}</p>
        <ConfigurationMarkdown :markdown="message" :admin="true" />
    </GPopover>
</template>

<style scoped>
button.object-store-badge-wrapper {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    line-height: inherit;
    cursor: default;
}
</style>
