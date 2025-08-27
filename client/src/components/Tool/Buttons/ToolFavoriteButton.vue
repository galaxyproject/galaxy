<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { ComponentColor } from "@/components/BaseComponents/componentVariants";
import { useToolsListCardActions } from "@/components/ToolsList/useToolsListCardActions";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    id: string;
    color?: ComponentColor;
    detailed?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    color: "blue",
});

const { favoriteToolAction: btn } = useToolsListCardActions(props.id);
</script>

<template>
    <GButton
        :id="btn.id"
        :color="props.color"
        :disabled="btn.disabled"
        :disabled-title="btn.title"
        tooltip
        size="small"
        :transparent="!props.detailed"
        :title="btn.title"
        @click="btn.handler">
        <FontAwesomeIcon :icon="btn.icon" />
        <span v-if="props.detailed">
            {{ btn.label }}
        </span>
    </GButton>
</template>
