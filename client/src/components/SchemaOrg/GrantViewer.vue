<template>
    <span itemprop="funding" itemscope itemtype="https://schema.org/Grant">
        <FontAwesomeIcon :id="popoverTarget" :icon="faCoins" />

        <GPopover triggers="click blur" :target="popoverTarget" title="Grant">
            <GTable :items="items" :fields="fields" />
        </GPopover>

        <span v-if="name" itemprop="name">{{ name }}</span>
        <span v-if="identifier" itemprop="identifier">({{ identifier }})</span>

        <GLink v-if="url" v-g-tooltip.hover tooltip title="Grant URL" :href="url" target="_blank">
            <link itemprop="url" :href="url" />
            <FontAwesomeIcon :icon="faExternalLinkAlt" />
        </GLink>

        <meta
            v-for="attribute in explicitMetaAttributes"
            :key="attribute.attribute"
            :itemprop="attribute.attribute"
            :content="attribute.value" />

        <slot name="buttons" />
    </span>
</template>

<script>
import { faCoins, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { useUid } from "@/composables/utils/uid";

import ThingViewerMixin from "./ThingViewerMixin";

import GLink from "@/components/BaseComponents/GLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";
import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        FontAwesomeIcon,
        GLink,
        GPopover,
        GTable,
    },
    mixins: [ThingViewerMixin],
    props: {
        grant: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            faCoins,
            faExternalLinkAlt,
            // An id, not a template ref: $refs is empty on first render and not reactive.
            popoverTarget: useUid("grant-viewer-").value,
            implicitMicrodataProperties: ["name", "identifier", "url"],
            thing: this.grant,
            fields: [
                { key: "attribute", label: "Attribute" },
                { key: "value", label: "Value" },
            ],
        };
    },
    computed: {
        name() {
            return this.grant.name;
        },
        identifier() {
            return this.grant.identifier;
        },
    },
};
</script>
