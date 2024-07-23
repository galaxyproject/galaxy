<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BRow } from "bootstrap-vue";

library.add(faCog);

const props = defineProps({
    id: {
        type: String,
        default: null,
    },
    icon: {
        type: String,
        default: "fa-cog",
    },
    title: {
        type: String,
        default: "Title not available.",
    },
    description: {
        type: String,
        default: "Description not available.",
    },
    to: {
        type: String,
        default: null,
    },
    badge: {
        type: String,
        default: null,
    },
});
</script>

<template>
    <BRow class="ml-3 mb-1">
        <FontAwesomeIcon class="pref-icon pt-1" :icon="props.icon" />
        <div class="pref-content pr-1">
            <b-badge v-if="Boolean(props.badge)" variant="danger">
                {{ props.badge }}
            </b-badge>
            <router-link v-if="Boolean(props.to)" :id="props.id" :to="props.to">
                <b v-localize> {{ props.title }} </b>
            </router-link>
            <button v-else :id="props.id" class="ui-link" @click="$emit('click')">
                <b v-localize> {{ props.title }} </b>
            </button>
            <div class="form-text text-muted">
                {{ props.description }}
            </div>
            <slot />
        </div>
    </BRow>
</template>
<style scoped>
.pref-content {
    width: calc(100% - 3rem);
}
.pref-icon {
    width: 3rem;
}
</style>
