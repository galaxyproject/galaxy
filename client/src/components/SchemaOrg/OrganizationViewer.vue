<template>
    <span itemprop="creator" itemscope itemtype="https://schema.org/Organization">
        <FontAwesomeIcon :id="popoverTarget" :icon="faBuilding" />

        <GPopover triggers="click blur" :target="popoverTarget" title="Organization">
            <GTable :items="items" :fields="fields" />
        </GPopover>

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

        <GLink v-if="url" v-g-tooltip.hover tooltip title="Organization URL" :href="url" target="_blank">
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

import { useUid } from "@/composables/utils/uid";

import ThingViewerMixin from "./ThingViewerMixin";

import GLink from "@/components/BaseComponents/GLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";
import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        GPopover,
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
            // An element id rather than a template ref: $refs is empty on first render and isn't
            // reactive, so a ref-based target never resolves until something re-renders.
            popoverTarget: useUid("organization-viewer-").value,
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
