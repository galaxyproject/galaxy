<template>
    <span itemprop="creator" itemscope itemtype="https://schema.org/Organization">
        <FontAwesomeIcon ref="button" :icon="faBuilding" />

        <BPopover triggers="click blur" :target="$refs['button'] || 'works-lazily'" title="Organization">
            <GTable :items="items" :fields="fields" />
        </BPopover>

        <span v-if="name">
            <span itemprop="name">{{ name }}</span>
            <span v-if="email">
                (
                <span itemprop="email" :content="organization.email">{{ email }}</span>
                )
            </span>
        </span>
        <span v-else-if="email" itemprop="email" :content="organization.email">
            {{ email }}
        </span>

        <GLink v-if="url" v-b-tooltip.hover tooltip title="Organization URL" :href="url" target="_blank">
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
import { faBuilding, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
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
        organization: {
            type: Object,
        },
    },
    data() {
        return {
            faBuilding,
            faExternalLinkAlt,
            implicitMicrodataProperties: ["name", "email", "url", "identifier"],
            thing: this.organization,
            fields: [
                { key: "attribute", label: "Attribute" },
                { key: "value", label: "Value" },
            ],
        };
    },
    computed: {
        name() {
            return this.organization.name;
        },
    },
};
</script>
