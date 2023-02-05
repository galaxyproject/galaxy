<script setup>
import { computed, ref } from "vue";
import { copyLink, copyId, downloadTool, openLink } from "../utilities";
import { useCurrentUser } from "composables/user";
import Webhooks from "utils/webhooks";
import ToolSourceMenuItem from "components/Tool/ToolSourceMenuItem";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const { currentUser: user } = useCurrentUser(false, true);

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

const showDownload = computed(() => user.value?.is_admin);
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

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faLink, faDownload, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { faCopy } from "@fortawesome/free-regular-svg-icons";

library.add(faCaretDown, faLink, faDownload, faExternalLinkAlt, faCopy);
</script>

<template>
    <b-dropdown
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

        <b-dropdown-item @click="onCopyLink">
            <FontAwesomeIcon icon="fa-link" /><span v-localize>Copy Link</span>
        </b-dropdown-item>

        <b-dropdown-item @click="onCopyId">
            <FontAwesomeIcon icon="far fa-copy" /><span v-localize>Copy Tool ID</span>
        </b-dropdown-item>

        <b-dropdown-item v-if="showDownload" @click="onDownload">
            <FontAwesomeIcon icon="fa-download" /><span v-localize>Download</span>
        </b-dropdown-item>

        <ToolSourceMenuItem :tool-id="id" />

        <b-dropdown-item v-if="showLink" @click="onLink">
            <FontAwesomeIcon icon="fa-external-link-alt" /><span v-localize>See in Tool Shed</span>
        </b-dropdown-item>

        <b-dropdown-item v-for="w of webhookDetails" :key="w.title" @click="w.onclick">
            <span :class="w.icon" />{{ l(w.title) }}
        </b-dropdown-item>
    </b-dropdown>
</template>
