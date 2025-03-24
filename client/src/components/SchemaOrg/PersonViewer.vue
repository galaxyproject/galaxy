<template>
    <span itemprop="creator" itemscope itemtype="https://schema.org/Person">
        <FontAwesomeIcon ref="button" icon="user" />
        <b-popover
            triggers="click blur"
            :placement="hoverPlacement"
            :target="$refs['button'] || 'works-lazily'"
            title="个人信息">
            <b-table striped :items="items"> </b-table>
        </b-popover>
        <span v-if="name">
            <meta v-if="person.name" itemprop="name" :content="person.name" />
            <meta v-if="person.givenName" itemprop="givenName" :content="person.givenName" />
            <meta v-if="person.familyName" itemprop="familyName" :content="person.familyName" />
            {{ name }}
            <span v-if="email">
                (<span itemprop="email" :content="person.email">{{ email }}</span
                >)
            </span>
        </span>
        <span v-else itemprop="email" :content="person.email">
            {{ email }}
        </span>
        <a v-if="orcidLink" v-b-tooltip.hover title="查看 orcid.org 个人资料" :href="orcidLink" target="_blank">
            <link itemprop="identifier" :href="orcidLink" />
            <FontAwesomeIcon :icon="['fab', 'orcid']" />
        </a>
        <a v-if="url" v-b-tooltip.hover title="网址" :href="url" target="_blank">
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
import { faOrcid } from "@fortawesome/free-brands-svg-icons";
import { faExternalLinkAlt, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import ThingViewerMixin from "./ThingViewerMixin";

library.add(faOrcid, faUser, faExternalLinkAlt);

export default {
    components: {
        FontAwesomeIcon,
    },
    mixins: [ThingViewerMixin],
    props: {
        person: {
            type: Object,
        },
        hoverPlacement: {
            type: String,
            default: "left",
        },
    },
    data() {
        return {
            implicitMicrodataProperties: ["name", "givenName", "email", "familyName", "url", "identifier"],
            thing: this.person,
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
