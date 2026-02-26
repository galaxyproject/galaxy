<template>
    <span itemprop="creator" itemscope itemtype="https://schema.org/Person">
        <FontAwesomeIcon ref="button" :icon="faUser" />

        <BPopover triggers="click blur" :target="$refs['button'] || 'works-lazily'" title="Person">
            <GTable :items="items" :fields="fields" />
        </BPopover>

        <span v-if="name">
            <meta v-if="person.name" itemprop="name" :content="person.name" />
            <meta v-if="person.givenName" itemprop="givenName" :content="person.givenName" />
            <meta v-if="person.familyName" itemprop="familyName" :content="person.familyName" />
            {{ name }}
            <span v-if="email">
                (
                <span itemprop="email" :content="person.email">{{ email }}</span>
                )
            </span>
        </span>
        <span v-else itemprop="email" :content="person.email">
            {{ email }}
        </span>

        <GLink
            v-if="orcidLink"
            v-b-tooltip.hover
            tooltip
            title="View orcid.org profile"
            :href="orcidLink"
            target="_blank">
            <link itemprop="identifier" :href="orcidLink" />
            <FontAwesomeIcon :icon="faOrcid" />
        </GLink>
        <GLink v-if="url" v-b-tooltip.hover tooltip title="URL" :href="url" target="_blank">
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
import { faOrcid } from "@fortawesome/free-brands-svg-icons";
import { faExternalLinkAlt, faUser } from "@fortawesome/free-solid-svg-icons";
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
        person: {
            type: Object,
        },
    },
    data() {
        return {
            faOrcid,
            faUser,
            faExternalLinkAlt,
            implicitMicrodataProperties: ["name", "givenName", "email", "familyName", "url", "identifier"],
            thing: this.person,
            fields: [
                { key: "attribute", label: "Attribute" },
                { key: "value", label: "Value" },
            ],
        };
    },
    computed: {
        name() {
            let name = this.person.name;
            const familyName = this.person.familyName;
            const givenName = this.person.givenName;
            if (name == null && (familyName || givenName)) {
                const honorificPrefix = this.person.honorificPrefix;
                const honorificSuffix = this.person.honorificSuffix;
                if (givenName && familyName) {
                    name = givenName + " " + familyName;
                } else if (givenName) {
                    name = givenName;
                } else {
                    name = familyName;
                }
                if (honorificPrefix) {
                    name = honorificPrefix + " " + name;
                }
                if (honorificSuffix) {
                    name = name + " " + honorificSuffix;
                }
            }
            return name;
        },
        orcidLink() {
            const identifier = this.person.identifier;
            // Maybe interpret any XXXX-XXXX-XXXX-XXXX as orcid ID?
            if (identifier && identifier.indexOf("orcid.org/") >= 0) {
                return identifier;
            } else {
                return null;
            }
        },
    },
};
</script>
