<script setup>
import { computed, ref } from "vue";
import { copyLink, copyId, downloadTool, openLink } from "../utilities";
import { useCurrentUser } from "composables/user";
import Webhooks from "mvc/webhooks";
import ToolSourceMenuItem from "components/Tool/ToolSourceMenuItem";

const user = useCurrentUser();

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
    sharableUrl: {
        type: String,
        default: null,
    },
});

const webhookDetails = ref([]);

Webhooks.load({
    type: "tool-menu",
    callback: (webhooks) => {
        webhooks.each((model) => {
            const webhook = model.toJSON();

            if (webhook.activate && webhook.config.function) {
                webhookDetails.value = {
                    icon: `fa ${webhook.config.icon}`,
                    title: webhook.config.title,
                    onclick: () => {
                        const func = new Function("options", webhook.config.function);
                        func(props.options);
                    },
                };
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
            <icon icon="caret-down" />
        </template>

        <b-dropdown-item @click="onCopyLink"> <icon icon="link" /><span v-localize>Copy Link</span> </b-dropdown-item>

        <b-dropdown-item @click="onCopyId">
            <icon icon="far fa-copy" /><span v-localize>Copy Tool ID</span>
        </b-dropdown-item>

        <b-dropdown-item v-if="showDownload" @click="onDownload">
            <icon icon="download" /><span v-localize>Download</span>
        </b-dropdown-item>

        <ToolSourceMenuItem :tool-id="id" />

        <b-dropdown-item v-if="showLink" @click="onLink">
            <icon icon="external-link-alt" /><span v-localize>See in Tool Shed</span>
        </b-dropdown-item>

        <b-dropdown-item v-for="w of webhookDetails" :key="w.title" @click="w.onclick">
            <span :class="w.icon" />{{ l(w.title) }}
        </b-dropdown-item>
    </b-dropdown>
</template>
