<script setup lang="ts">
/* global __buildTimestamp__, __license__  */
/* (injected by webpack) */

import { computed } from "vue";
import { RouterLink } from "vue-router";

import { useConfig } from "@/composables/config";
import { getAppRoot } from "@/onload/loadConfig";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import License from "@/components/License/License.vue";
import UtcDate from "@/components/UtcDate.vue";

const { config, isConfigLoaded } = useConfig();

const clientBuildDate = __buildTimestamp__ || new Date().toISOString();
const apiDocsLink = `${getAppRoot()}api/docs`;
const galaxyLicense = __license__;

const versionUserDocumentationUrl = computed(() => {
    const configVal = config.value;
    return config.value.version_minor.slice(0, 3) === "dev"
        ? "https://docs.galaxyproject.org/en/latest/releases/index.html"
        : `${configVal.release_doc_base_url}${configVal.version_major}/releases/${configVal.version_major}_announce_user.html`;
});
</script>

<template>
    <div v-if="isConfigLoaded" class="about-galaxy">
        <Heading h1 :icon="['gxd', 'galaxyLogo']" size="xl">Help and Support</Heading>
        <div class="py-4">
            <div v-if="config.wiki_url">
                <Heading h2 separator size="md">Community Hub</Heading>
                <p>
                    Interact with the our community, explore and publish tutorials at
                    <ExternalLink :href="config.wiki_url">
                        {{ config.wiki_url }}
                    </ExternalLink>
                </p>
            </div>
            <div v-if="config.citation_url">
                <Heading h2 separator size="md">How to Cite Us</Heading>
                <p>
                    Find more details on how to properly cite Galaxy at
                    <ExternalLink :href="config.citation_url">
                        {{ config.citation_url }}
                    </ExternalLink>
                </p>
            </div>
            <div>
                <Heading h2 separator size="md">Interactive Tours</Heading>
                <p>
                    Explore and learn about Galaxy through interactive
                    <RouterLink to="tours">tours</RouterLink>.
                </p>
            </div>
            <div v-if="config.screencasts_url">
                <Heading h2 separator size="md">Videos and Screencasts</Heading>
                <p>
                    Learn more about Galaxy by watching videos and screencasts at
                    <ExternalLink :href="config.screencasts_url">
                        {{ config.screencasts_url }}
                    </ExternalLink>
                </p>
            </div>
            <div v-if="config.helpsite_url">
                <Heading h2 separator size="md">User Documentation</Heading>
                <p>
                    Learn more about Galaxy at
                    <ExternalLink :href="config.helpsite_url">
                        {{ config.helpsite_url }}
                    </ExternalLink>
                </p>
            </div>
            <div>
                <Heading h2 separator size="md">API Documentation</Heading>
                <!-- API documentation link -->
                <p>
                    The Galaxy API is available, and explorable, at
                    <ExternalLink :href="apiDocsLink">
                        {{ apiDocsLink }}
                    </ExternalLink>
                </p>
            </div>
            <div>
                <!-- Galaxy version (detailed), with a link to the release notes -->
                <Heading h2 separator size="md">Version Information</Heading>
                <p>
                    The Galaxy Server is running version
                    <ExternalLink :href="versionUserDocumentationUrl">
                        <strong> {{ config.version_major }}.{{ config.version_minor }}</strong> </ExternalLink
                    >, and the web client was built on <UtcDate :date="clientBuildDate" mode="pretty" />.
                </p>
                <template v-if="config.version_extra">
                    <p>The server also provides the following extra version information</p>
                    <ul>
                        <li v-for="(value, name, index) in config.version_extra" :key="index">
                            <strong>{{ name }}</strong>
                            : {{ value }}
                        </li>
                    </ul>
                </template>
            </div>
            <div>
                <Heading h2 separator size="md">License Information</Heading>
                <p>The Galaxy Software is licensed under <License :license-id="galaxyLicense" /></p>
            </div>
            <div v-if="config.terms_url">
                <!-- Terms, if available.-->
                <Heading h2 separator size="md">Terms and Conditions</Heading>
                <p>
                    This Galaxy Server has specified Terms and Conditions that apply to use of the service.
                    <ExternalLink :href="config.terms_url">Review them here.</ExternalLink>
                </p>
            </div>
            <div v-if="config.support_url">
                <Heading h2 separator size="md">Support</Heading>
                <p>
                    Do you need help? Reach out at
                    <ExternalLink :href="config.support_url">
                        {{ config.support_url }}
                    </ExternalLink>
                </p>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.about-galaxy h1 {
    --fa-primary-color: #{$brand-primary};
    --fa-secondary-color: #{$brand-toggle};
    --fa-secondary-opacity: 1;
}
</style>
