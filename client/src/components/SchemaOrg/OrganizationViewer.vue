<template>
    <span itemprop="creator" itemscope itemtype="https://schema.org/Organization">
        <FontAwesomeIcon ref="button" icon="building" />
        <b-popover
            triggers="click blur"
            :placement="hoverPlacement"
            :target="$refs['button'] || 'works-lazily'"
            title="组织">
            <b-table striped :items="items"> </b-table>
        </b-popover>
        <span v-if="name">
            <span itemprop="name">{{ name }}</span>
            <span v-if="email">
                (<span itemprop="email" :content="organization.email">{{ email }}</span
                >)
            </span>
        </span>
        <span v-else-if="email" itemprop="email" :content="organization.email">
            {{ email }}
        </span>
        <a v-if="url" v-b-tooltip.hover title="组织网址" :href="url" target="_blank">
            <link itemprop="url" :href="url" />
            <FontAwesomeIcon icon="external-link-alt" />
        </a>
        <meta
            v-for="attribute in explicitMetaAttributes"
            :key="attribute.attribute"
            :itemprop="attribute.attribute"
            :content="attribute.value" />
        <slot name="buttons"></slot>
    </span>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import ThingViewerMixin from "./ThingViewerMixin";

library.add(faExternalLinkAlt, faBuilding);

export default {
    components: {
        FontAwesomeIcon,
    },
    mixins: [ThingViewerMixin],
    props: {
        organization: {
            type: Object,
        },
        hoverPlacement: {
            type: String,
            default: "left",
        },
    },
    data() {
        return {
            implicitMicrodataProperties: ["name", "email", "url", "identifier"],
            thing: this.organization,
        };
    },
    computed: {
        name() {
            return this.organization.name;
        },
    },
};
</script>
