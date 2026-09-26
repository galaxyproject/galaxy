<template>
    <span itemprop="funding" itemscope itemtype="https://schema.org/Grant">
        <FontAwesomeIcon ref="button" :icon="faCoins" />

        <BPopover triggers="click blur" :target="$refs['button'] || 'works-lazily'" title="Grant">
            <GTable :items="items" :fields="fields" />
        </BPopover>

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
import { BPopover } from "bootstrap-vue";

import ThingViewerMixin from "./ThingViewerMixin";

import GLink from "@/components/BaseComponents/GLink.vue";
import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        BPopover,
        FontAwesomeIcon,
        GLink,
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
