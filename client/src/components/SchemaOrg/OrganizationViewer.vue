<template>
    <span itemprop="creator" itemscope itemtype="https://schema.org/Organization">
        <b-button ref="button"
            v-b-modal.organization-details
            class="py-0 px-1"
            size="sm"
            variant="link"
            title="Organization details">
            <FontAwesomeIcon icon="building" fixed-width/>
        </b-button>
        <b-modal id="organization-details" title="Organization" hide-footer>
            <b-table striped :items="items"> </b-table>
        </b-modal>
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
        <a v-if="url" v-b-tooltip.hover title="Organization URL" :href="url" target="_blank">
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
