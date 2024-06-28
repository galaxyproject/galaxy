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
        <div class="p-2">
            <Heading h2 separator size="md">Support</Heading>
            <div v-if="config.wiki_url">
                <ExternalLink :href="config.wiki_url">
                    <strong>Community Hub</strong>
                </ExternalLink>
                <p>
                    Interact with the our community, learn how to use Galaxy through tutorials or publish your own ones.
                </p>
            </div>
            <div v-if="config.helpsite_url">
                <ExternalLink :href="config.helpsite_url">
                    <strong>Ask Questions & Find Answers</strong>
                </ExternalLink>
                <p>Access the Galaxy Q&A website.</p>
            </div>
            <div v-if="config.support_url">
                <ExternalLink :href="config.support_url">
                    <strong>Reach Out</strong>
                </ExternalLink>
                <p>Do you need help? Do you want to teach or learn more about Galaxy? Feel free to reach out.</p>
            </div>
            <Heading h2 separator size="md">Help</Heading>
            <div>
                <RouterLink to="tours">
                    <strong>Interactive Tours</strong>
                </RouterLink>
                <p>Explore and learn about Galaxy through interactive tours.</p>
            </div>
            <div v-if="config.screencasts_url">
                <ExternalLink :href="config.screencasts_url">
                    <strong>Videos and Screencasts</strong>
                </ExternalLink>
                <p>Learn more about Galaxy by watching videos and screencasts.</p>
            </div>
            <div v-if="config.citation_url">
                <ExternalLink :href="config.citation_url">
                    <strong>How to Cite Us</strong>
                </ExternalLink>
                <p>View details on how to properly cite Galaxy.</p>
            </div>
            <Heading h2 separator size="md">Technical Details</Heading>
            <div>
                <!-- Galaxy version (detailed), with a link to the release notes -->
                <ExternalLink :href="versionUserDocumentationUrl">
                    <strong>Release Notes</strong>
                </ExternalLink>
                <p>
                    This Galaxy server version is <strong>{{ config.version_major }}.{{ config.version_minor }}</strong
                    >, and the web client was built on
                    <strong><UtcDate :date="clientBuildDate" mode="pretty" /></strong>.
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
                <ExternalLink :href="apiDocsLink">
                    <strong>API Documentation</strong>
                </ExternalLink>
                <p>Explore the Galaxy API.</p>
            </div>
            <div>
                <License class="font-weight-bold" :license-id="galaxyLicense" />
                <p>The Galaxy Software is licensed under the MIT License.</p>
            </div>
            <div v-if="config.terms_url">
                <!-- Terms, if available.-->
                <ExternalLink :href="config.terms_url">
                    <strong>Terms and Conditions</strong>
                </ExternalLink>
                <p>This Galaxy Server has specified Terms and Conditions that apply to use of the service.</p>
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
