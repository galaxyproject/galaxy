<script setup>
/* global __buildTimestamp__, __license__  */
/* (injected by webpack) */

import { computed } from "vue";

import { getAppRoot } from "onload/loadConfig";
import { useConfig } from "components/composables/useConfig";
import UtcDate from "components/UtcDate";
import License from "components/License/License";
import ExternalLink from "components/ExternalLink";

const { config, isLoaded } = useConfig();

const clientBuildDate = __buildTimestamp__ || new Date();
const apiDocsLink = `${getAppRoot()}api/docs`;
const galaxyLicense = __license__;

const versionUserDocumentationUrl = computed(() => {
    const configVal = config.value;
    return config.value.version_minor.slice(0, 3) == "dev"
        ? "https://docs.galaxyproject.org/en/latest/releases/index.html"
        : `${configVal.release_doc_base_url}${configVal.version_major}/releases/${configVal.version_major}_announce_user.html`;
});

const versionExtra = computed(() => {
    const configVal = config.value;
    return Object.entries(configVal.version_extra);
});
</script>

<template>
    <div v-if="isLoaded">
        <h1>About This Galaxy</h1>
        <div>
            <!-- Galaxy version (detailed), with a link to the release notes -->
            <h4>Galaxy Version Information</h4>
            <p>
                The Galaxy Server is running version
                <external-link :href="versionUserDocumentationUrl">
                    <strong> {{ config.version_major }}.{{ config.version_minor }}</strong> </external-link
                >, and the web client was built on <UtcDate :date="clientBuildDate" mode="pretty" />.
            </p>
            <template v-if="config.version_extra">
                <p>The server also provides the following extra version information</p>
                <b-table :striped="true" thead-class="d-none" :items="versionExtra" />
            </template>
        </div>
        <div>
            <h4>Galaxy API Documentation</h4>
            <!-- API documentation link -->
            <p>
                The Galaxy API is available, and explorable, at
                <external-link :href="apiDocsLink">
                    {{ apiDocsLink }}
                </external-link>
            </p>
        </div>
        <div>
            <h4>License Information</h4>
            <p>The Galaxy Software is licensed under <License :license-id="galaxyLicense" /></p>
        </div>
        <div v-if="config.terms_url">
            <!-- Terms, if available.-->
            <p>This Galaxy instance has set terms of use. Please review them below.</p>
            <hr />
            <b-embed type="iframe" :src="config.terms_url" aspect="1by1" />
        </div>
    </div>
</template>
