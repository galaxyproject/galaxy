<script setup lang="ts">
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import type { PropType } from "vue";

const props = defineProps({
    id: {
        type: String,
        default: null,
    },
    icon: {
        type: String as PropType<any>,
        default: faCog,
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
    <section>
        <FontAwesomeIcon class="pref-icon" size="lg" :icon="props.icon" />
        <div class="pref-content">
            <h2>
                <BBadge v-if="Boolean(props.badge)" variant="danger">
                    {{ props.badge }}
                </BBadge>

                <router-link v-if="Boolean(props.to)" :id="props.id" :to="props.to">
                    <b v-localize> {{ props.title }} </b>
                </router-link>

                <button v-else :id="props.id" class="ui-link" @click="$emit('click')">
                    <b v-localize> {{ props.title }} </b>
                </button>
            </h2>

            <div class="description">
                {{ props.description }}
            </div>
            <slot />
        </div>
    </section>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

section {
    display: grid;
    grid-template-columns: 3rem 1fr;
    margin-bottom: 1rem;
}

.pref-icon {
    justify-self: center;
}

h2 {
    font-size: $font-size-base;
    margin-bottom: 0;
}

.description {
    margin-top: 0.25rem;
    color: $text-muted;
}
</style>
