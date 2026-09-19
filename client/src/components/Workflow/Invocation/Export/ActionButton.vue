<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import type { InvocationExportPluginAction } from "@/components/Workflow/Invocation/Export/Plugins";

import GButton from "@/components/BaseComponents/GButton.vue";

const modal = ref();

interface Props {
    action: InvocationExportPluginAction;
}

const props = defineProps<Props>();
</script>

<template>
    <GButton
        v-g-tooltip.hover.bottom
        :title="props.action.title"
        :icon-only="!!props.action.icon"
        @click="props.action.run(modal)">
        <FontAwesomeIcon v-if="props.action.icon" :icon="props.action.icon" />
        <div v-else>
            {{ props.action.title }}
        </div>
        <component :is="props.action.modal" v-if="props.action.modal" ref="modal" />
    </GButton>
</template>
