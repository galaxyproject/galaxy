<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faGlobe, faLink, faShareAlt, faUsers } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, VBTooltip } from "bootstrap-vue";

library.add(faGlobe, faShareAlt, faLink, faUsers);

interface SharingIndicatorsProps {
    object: Object;
}
const props = defineProps<SharingIndicatorsProps>();
</script>

<template>
    <span>
        <BButton
            v-if="props.object.published"
            v-b-tooltip.hover.noninteractive
            class="sharing-indicator-published"
            size="sm"
            variant="link"
            :title="'Find all published items' | localize"
            @click.prevent="$emit('filter', 'published')">
            <FontAwesomeIcon icon="globe" />
        </BButton>
        <BButton
            v-if="props.object.importable"
            v-b-tooltip.hover.noninteractive
            class="sharing-indicator-importable"
            size="sm"
            variant="link"
            :title="'Find all importable items' | localize"
            @click.prevent="$emit('filter', 'importable')">
            <FontAwesomeIcon icon="link" />
        </BButton>
        <BButton
            v-if="props.object.shared"
            v-b-tooltip.hover.noninteractive
            class="sharing-indicator-shared"
            size="sm"
            variant="link"
            :title="'Find all items shared with me' | localize"
            @click.prevent="$emit('filter', 'shared_with_me')">
            <FontAwesomeIcon icon="share-alt" />
        </BButton>
    </span>
</template>
