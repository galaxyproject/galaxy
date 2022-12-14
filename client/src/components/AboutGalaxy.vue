<script setup lang="ts">
/* global __buildTimestamp__, __license__  */
/* (injected by webpack) */

import { computed } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useConfig } from "@/composables/config";
import UtcDate from "@/components/UtcDate.vue";
import License from "@/components/License/License.vue";
import ExternalLink from "@/components/ExternalLink.vue";

const { config, isLoaded } = useConfig();

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
    <div v-if="isLoaded">
        <h1>About This Galaxy</h1>
        <div>
            <!-- Galaxy version (detailed), with a link to the release notes -->
            <h2>Galaxy Version Information</h2>
            <p>
                The Galaxy Server is running version
                <external-link :href="versionUserDocumentationUrl">
                    <strong> {{ config.version_major }}.{{ config.version_minor }}</strong> </external-link
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
            <h2>Galaxy API Documentation</h2>
            <!-- API documentation link -->
            <p>
                The Galaxy API is available, and explorable, at
                <external-link :href="apiDocsLink">
                    {{ apiDocsLink }}
                </external-link>
            </p>
        </div>
        <div>
            <h2>License Information</h2>
            <p>The Galaxy Software is licensed under <License :license-id="galaxyLicense" /></p>
        </div>
        <div v-if="config.terms_url">
            <!-- Terms, if available.-->
            <h2>Terms and Conditions</h2>
            <p>
                This Galaxy Server has specified Terms and Conditions that apply to use of the service.
                <external-link :href="config.terms_url">Review them here.</external-link>
            </p>
        </div>
    </div>
</template>
