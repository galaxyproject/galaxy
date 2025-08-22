<script setup lang="ts">
import { faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { getFullAppUrl } from "@/app/utils";
import type { ComponentColor } from "@/components/BaseComponents/componentVariants";
import { Toast } from "@/composables/toast";
import { copy } from "@/utils/clipboard";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    id: string;
    name?: string;
    link?: string;
    version?: string;
    color?: ComponentColor;
    detailed?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    color: "blue",
    name: undefined,
    link: undefined,
    version: undefined,
});

function shareTool() {
    const copyableLink = props.link
        ? getFullAppUrl(props.link?.substring(1))
        : getFullAppUrl(`?tool_id=${encodeURIComponent(props.id)}${props.version ? `&version=${props.version}` : ""}`);
    copy(copyableLink);
    Toast.success(`Link to ${props.name || "tool"} copied to clipboard`);
}
</script>

<template>
    <GButton
        :color="props.color"
        tooltip
        size="small"
        :transparent="!props.detailed"
        title="Copy link to tool"
        @click="shareTool">
        <FontAwesomeIcon :icon="faLink" />
        <span v-if="props.detailed"> Copy link </span>
    </GButton>
</template>
