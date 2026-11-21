<!-- https://schema.org/isBasedOn -->
<script setup lang="ts">
import { faCodeBranch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { BasedOnWork } from "@/api/workflows";

import CreatorViewer from "./CreatorViewer.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

const props = defineProps<{
    work: BasedOnWork;
}>();

const identifierLink = computed(() => {
    const identifier = props.work.identifier;
    if (identifier?.startsWith("doi:")) {
        return `https://doi.org/${identifier.slice("doi:".length)}`;
    }
    return identifier?.includes("://") ? identifier : null;
});
</script>

<template>
    <span class="based-on-work" itemprop="isBasedOn" itemscope :itemtype="`https://schema.org/${work.class}`">
        <FontAwesomeIcon :icon="faCodeBranch" />
        <GLink v-if="work.url" :href="work.url" target="_blank" title="Open upstream work">
            <link itemprop="url" :href="work.url" />
            <span itemprop="name">{{ work.name }}</span>
        </GLink>
        <span v-else itemprop="name">{{ work.name }}</span>
        <span v-if="work.version">
            <meta itemprop="version" :content="work.version" />
            (version {{ work.version }})
        </span>
        <GLink v-if="identifierLink" :href="identifierLink" target="_blank" title="Open identifier">
            <link itemprop="identifier" :href="identifierLink" />
            {{ work.identifier }}
        </GLink>
        <span v-else-if="work.identifier" itemprop="identifier">{{ work.identifier }}</span>
        <span v-if="work.license">
            <meta itemprop="license" :content="work.license" />
            - license {{ work.license }}
        </span>
        <slot name="buttons" />
        <ul v-if="work.creator?.length" class="based-on-creators list-unstyled mb-0 ml-3">
            <li v-for="(creator, index) in work.creator" :key="index">
                <CreatorViewer :creator="creator" />
            </li>
        </ul>
    </span>
</template>
