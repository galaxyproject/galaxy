<script setup lang="ts">
import { faGlobe, faLink, faShareAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GButton from "@/components/BaseComponents/GButton.vue";

interface SharingIndicatorsProps {
    object: {
        deleted?: boolean;
        importable?: boolean;
        published?: boolean;
        purged?: boolean;
        shared?: boolean;
    };
}
const props = defineProps<SharingIndicatorsProps>();
</script>

<template>
    <span v-if="props.object.purged" v-localize> Purged </span>
    <span v-else-if="props.object.deleted" v-localize> Deleted </span>
    <span v-else>
        <GButton
            v-if="props.object.published"
            v-g-tooltip.hover
            class="sharing-indicator-published"
            size="small"
            transparent
            icon-only
            title="Find all published items"
            @click.prevent="$emit('filter', 'published')">
            <FontAwesomeIcon :icon="faGlobe" />
        </GButton>
        <GButton
            v-if="props.object.importable"
            v-g-tooltip.hover
            class="sharing-indicator-importable"
            size="small"
            transparent
            icon-only
            title="Find all importable items"
            @click.prevent="$emit('filter', 'importable')">
            <FontAwesomeIcon :icon="faLink" />
        </GButton>
        <GButton
            v-if="props.object.shared"
            v-g-tooltip.hover
            class="sharing-indicator-shared"
            size="small"
            transparent
            icon-only
            title="Find all items shared with me"
            @click.prevent="$emit('filter', 'shared_with_me')">
            <FontAwesomeIcon :icon="faShareAlt" />
        </GButton>
    </span>
</template>
