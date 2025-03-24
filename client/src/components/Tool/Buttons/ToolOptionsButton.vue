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
    copyLink(props.id, "链接已复制到剪贴板");
}

function onCopyId() {
    copyId(props.id, "工具 ID 已复制到剪贴板");
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
        title="选项"
        variant="link"
        aria-label="查看所有选项"
        class="tool-dropdown"
        size="sm">
        <template v-slot:button-content>
            <FontAwesomeIcon icon="fa-caret-down" />
        </template>

        <b-dropdown-item @click="onCopyLink">
            <FontAwesomeIcon icon="fa-link" /><span v-localize>复制链接</span>
        </b-dropdown-item>

        <b-dropdown-item @click="onCopyId">
            <FontAwesomeIcon icon="far fa-copy" /><span v-localize>复制工具ID</span>
        </b-dropdown-item>

        <b-dropdown-item v-if="showDownload" @click="onDownload">
            <FontAwesomeIcon icon="fa-download" /><span v-localize>下载</span>
        </b-dropdown-item>

        <ToolSourceMenuItem :tool-id="id" />

        <b-dropdown-item v-if="showLink" @click="onLink">
            <FontAwesomeIcon icon="fa-external-link-alt" /><span v-localize>在工具库中查看</span>
        </b-dropdown-item>

        <b-dropdown-item v-for="w of webhookDetails" :key="w.title" @click="w.onclick">
            <span :class="w.icon" />{{ l(w.title) }}
        </b-dropdown-item>
    </b-dropdown>
</template>
