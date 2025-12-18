<script setup lang="ts">
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { faCaretDown, faDownload, faExternalLinkAlt, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { isAdminUser } from "@/api";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { loadWebhooks } from "@/utils/webhooks";

import { copyId, copyLink, downloadTool, openLink } from "../utilities";

import ToolTourGeneratorItem from "./ToolTourGeneratorItem.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import ToolSourceMenuItem from "@/components/Tool/ToolSourceMenuItem.vue";

const { currentUser } = storeToRefs(useUserStore());

interface Props {
    id: string;
    toolUuid?: string | null;
    sharableUrl?: string | null;
    options: Record<string, any>;
    allowGeneratedTours?: boolean;
    version?: string;
}

const props = withDefaults(defineProps<Props>(), {
    toolUuid: null,
    sharableUrl: null,
    version: "1.0",
});

const webhookDetails = ref<any[]>([]);

const showDownload = computed(() => isAdminUser(currentUser.value));
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

async function loadToolMenuWebhooks() {
    const webhooks = await loadWebhooks("tool-menu");
    webhooks.forEach((webhook: any) => {
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
}

loadToolMenuWebhooks();
</script>

<template>
    <BDropdown
        no-caret
        right
        role="button"
        title="Options"
        variant="link"
        aria-label="View all Options"
        class="tool-dropdown"
        toggle-class="p-0"
        size="sm">
        <template v-slot:button-content>
            <GButton class="d-block" color="blue" transparent size="small" tooltip title="Options">
                <FontAwesomeIcon :icon="faCaretDown" />
            </GButton>
        </template>

        <BDropdownItem @click="onCopyLink">
            <FontAwesomeIcon :icon="faLink" /><span v-localize>Copy Link</span>
        </BDropdownItem>

        <BDropdownItem @click="onCopyId">
            <FontAwesomeIcon :icon="faCopy" /><span v-localize>Copy Tool ID</span>
        </BDropdownItem>

        <BDropdownItem v-if="showDownload" @click="onDownload">
            <FontAwesomeIcon :icon="faDownload" /><span v-localize>Download</span>
        </BDropdownItem>

        <ToolSourceMenuItem :tool-id="id" :tool-uuid="toolUuid || undefined" />

        <BDropdownItem v-if="showLink" @click="onLink">
            <FontAwesomeIcon :icon="faExternalLinkAlt" /><span v-localize>See in Tool Shed</span>
        </BDropdownItem>

        <ToolTourGeneratorItem v-if="props.allowGeneratedTours" :tool-id="props.id" :tool-version="props.version" />

        <BDropdownItem v-for="w of webhookDetails" :key="w.title" @click="w.onclick">
            <span :class="w.icon" />{{ localize(w.title) }}
        </BDropdownItem>
    </BDropdown>
</template>
