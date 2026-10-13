<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import localize from "@/utils/localization";

import ToolLinkPopover from "./ToolLinkPopover.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

interface Props {
    /**
     * Id of the tool the popover links to
     */
    toolId: string;
    /**
     * Id for the button
     * @default undefined
     */
    id?: string;
    /**
     * Version of the tool the popover links to
     * @default undefined
     */
    toolVersion?: string;
}

withDefaults(defineProps<Props>(), {
    id: undefined,
    toolVersion: undefined,
});

const button = ref<InstanceType<typeof GLink> | null>(null);

// A stable function, so the popover doesn't rebind to the same button on every render.
const popoverTarget = () => button.value;
</script>

<template>
    <!-- Two roots, so the button and the popover host sit inline where the caller puts them. -->
    <GLink :id="id" ref="button" dark thin type="button" :aria-label="localize('Tool details')">
        <slot>
            <FontAwesomeIcon :icon="faInfoCircle" size="sm" />
        </slot>
    </GLink>

    <ToolLinkPopover interactive :target="popoverTarget" :tool-id="toolId" :tool-version="toolVersion" />
</template>
