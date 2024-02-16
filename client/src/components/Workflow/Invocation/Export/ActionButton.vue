<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { InvocationExportPluginAction } from "./model";

const modal = ref(null);

const props = defineProps({
    action: { type: InvocationExportPluginAction, required: true },
});
</script>

<template>
    <b-button v-b-tooltip.hover.bottom :title="props.action.title" @click="props.action.run(modal)">
        <FontAwesomeIcon v-if="props.action.icon" :icon="props.action.icon" />
        <div v-else>
            {{ props.action.title }}
        </div>
        <component :is="props.action.modal" v-if="props.action.modal" ref="modal" />
    </b-button>
</template>
