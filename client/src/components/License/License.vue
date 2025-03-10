<template>
    <LoadingSpan v-if="license == null" message="Loading license information"> </LoadingSpan>
    <span v-else-if="license.name" class="text-muted">
        <link itemprop="license" :href="license.licenseId" />
        <span v-if="title">
            {{ title }}
        </span>
        <ExternalLink :href="license.url">
            {{ license.name }}
        </ExternalLink>
        <slot name="buttons"></slot>
    </span>
    <span v-else>
        Unknown License (<i>{{ license.url }}</i
        >)
        <slot name="buttons"></slot>
    </span>
</template>

<script>
import ExternalLink from "components/ExternalLink";
import LoadingSpan from "components/LoadingSpan";

import { GalaxyApi } from "@/api";

export default {
    components: {
        LoadingSpan,
        ExternalLink,
    },
    props: {
        licenseId: {
            type: String,
            required: true,
        },
        inputLicenseInfo: {
            type: Object,
            required: false,
        },
        title: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            license: this.inputLicenseInfo,
        };
    },
    watch: {
        licenseId: function (newLicense, oldLicense) {
            if (newLicense != oldLicense) {
                this.fetchLicense();
            }
        },
    },
    created() {
        if (this.license == null) {
            this.fetchLicense();
        }
    },
    methods: {
        fetchLicense() {
            this.license = null;
            GalaxyApi()
                .GET("/api/licenses/{license_id}", {
                    params: {
                        path: {
                            license_id: this.licenseId,
                        },
                    },
                })
                .then((response) => response.data)
                .then((data) => {
                    this.license = data;
                });
        },
    },
};
</script>

<style></style>
