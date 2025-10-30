<script setup lang="ts">
import { faGlobe, faLink, faShareAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

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
        <BButton
            v-if="props.object.published"
            v-b-tooltip.hover.noninteractive
            class="sharing-indicator-published"
            size="sm"
            variant="link"
            title="Find all published items"
            @click.prevent="$emit('filter', 'published')">
            <FontAwesomeIcon :icon="faGlobe" />
        </BButton>
        <BButton
            v-if="props.object.importable"
            v-b-tooltip.hover.noninteractive
            class="sharing-indicator-importable"
            size="sm"
            variant="link"
            title="Find all importable items"
            @click.prevent="$emit('filter', 'importable')">
            <FontAwesomeIcon :icon="faLink" />
        </BButton>
        <BButton
            v-if="props.object.shared"
            v-b-tooltip.hover.noninteractive
            class="sharing-indicator-shared"
            size="sm"
            variant="link"
            title="Find all items shared with me"
            @click.prevent="$emit('filter', 'shared_with_me')">
            <FontAwesomeIcon :icon="faShareAlt" />
        </BButton>
    </span>
</template>
