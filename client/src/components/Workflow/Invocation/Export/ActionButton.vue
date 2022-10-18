<script setup>
import { InvocationExportPluginAction } from "./model";
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const modal = ref(null);

const props = defineProps({
    action: { type: InvocationExportPluginAction, required: true },
});
</script>

<template>
    <b-button v-b-tooltip.hover.bottom :title="props.action.title" @click="props.action.run(modal)">
        <font-awesome-icon v-if="props.action.icon" :icon="props.action.icon" />
        <div v-else>
            {{ props.action.title }}
        </div>
        <component :is="props.action.modal" v-if="props.action.modal" ref="modal" />
    </b-button>
</template>
