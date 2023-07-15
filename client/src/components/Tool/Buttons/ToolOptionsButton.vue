<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { faCaretDown, faDownload, faExternalLinkAlt, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import ToolSourceMenuItem from "components/Tool/ToolSourceMenuItem";
import { storeToRefs } from "pinia";
import Webhooks from "utils/webhooks";
import { computed, ref } from "vue";

import { useUserStore } from "@/stores/userStore";

import { copyId, copyLink, downloadTool, openLink } from "../utilities";

import GDropdown from "@/component-library/GDropdown.vue";
import GDropdownItem from "@/component-library/GDropdownItem.vue";

library.add(faCaretDown, faLink, faDownload, faExternalLinkAlt, faCopy);

const { currentUser } = storeToRefs(useUserStore());

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
    sharableUrl: {
        type: String,
        default: null,
    },
    options: {
        type: Object,
        required: true,
    },
});

const webhookDetails = ref([]);

Webhooks.load({
    type: "tool-menu",
    callback: (webhooks) => {
        webhooks.forEach((webhook) => {
            if (webhook.activate && webhook.config.function) {
                webhookDetails.value.push({
                    icon: `fa ${webhook.config.icon}`,
                    title: webhook.config.title,
                    onclick: () => {
                        const func = new Function("options", webhook.config.function);
                        func(props.options);
                    },
                });
            }
        });
    },
});

const showDownload = computed(() => currentUser.value?.is_admin);
const showLink = computed(() => Boolean(props.sharableUrl));

function onCopyLink() {
    copyLink(props.id, "Link was copied to your clipboard");
}

function onCopyId() {
    copyId(props.id, "Tool ID was copied to your clipboard");
}

function onDownload() {
    downloadTool(props.id);
}

function onLink() {
    openLink(props.sharableUrl);
}
</script>

<template>
    <GDropdown
        v-b-tooltip.hover
        no-caret
        right
        role="button"
        title="Options"
        variant="link"
        aria-label="View all Options"
        class="tool-dropdown"
        size="sm">
        <template v-slot:button-content>
            <FontAwesomeIcon icon="fa-caret-down" />
        </template>

        <GDropdownItem @click="onCopyLink">
            <FontAwesomeIcon icon="fa-link" /><span v-localize>Copy Link</span>
        </GDropdownItem>

        <GDropdownItem @click="onCopyId">
            <FontAwesomeIcon icon="far fa-copy" /><span v-localize>Copy Tool ID</span>
        </GDropdownItem>

        <GDropdownItem v-if="showDownload" @click="onDownload">
            <FontAwesomeIcon icon="fa-download" /><span v-localize>Download</span>
        </GDropdownItem>

        <ToolSourceMenuItem :tool-id="id" />

        <GDropdownItem v-if="showLink" @click="onLink">
            <FontAwesomeIcon icon="fa-external-link-alt" /><span v-localize>See in Tool Shed</span>
        </GDropdownItem>

        <GDropdownItem v-for="w of webhookDetails" :key="w.title" @click="w.onclick">
            <span :class="w.icon" />{{ l(w.title) }}
        </GDropdownItem>
    </GDropdown>
</template>
