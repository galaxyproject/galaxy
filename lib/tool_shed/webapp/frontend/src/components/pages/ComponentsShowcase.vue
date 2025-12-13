<script setup lang="ts">
import PageContainer from "@/components/PageContainer.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import ComponentShowcase from "@/components/ComponentShowcase.vue"
import ComponentShowcaseExample from "@/components/ComponentShowcaseExample.vue"
import RecentlyCreatedRepositories from "@/components/RecentlyCreatedRepositories.vue"
import RepositoryLink from "@/components/RepositoryLink.vue"
import RepositoryActions from "@/components/RepositoryActions.vue"
import LandingSearchBox from "@/components/LandingSearchBox.vue"
import LandingInfoSections from "@/components/LandingInfoSections.vue"
</script>

<template>
    <page-container>
        This page is only meant for tool shed developers. It demonstrates common widgets and styles in isolation.

        <component-showcase title="LoadingDiv">
            <component-showcase-example title="default">
                <loading-div />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="with supplied message">
                <loading-div message="I'm loading" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="ErrorBanner">
            <component-showcase-example title="default error message">
                <error-banner error="My Cool Error Message" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="long error message">
                <error-banner
                    error="This is a very long error message that might wrap or cause layout issues in the UI, but should still be displayed correctly to the user with proper formatting and readability."
                />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="error with special characters">
                <error-banner error="Error: &lt;script&gt;alert('xss')&lt;/script&gt; & 'quotes' &amp; symbols" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="RepositoryLink">
            <component-showcase-example title="Default Longer Repo">
                <repository-link id="1" owner="iuc" name="compute_motif_frequencies_for_all_motifs" />
            </component-showcase-example>
            <component-showcase-example title="Default Shorter Repo">
                <repository-link id="1" owner="devteam" name="ccat" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="RepositoryActions">
            <component-showcase-example title="defaults">
                <repository-actions repository-id="abcd" :deprecated="true" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="RecentlyCreatedRepositories">
            <component-showcase-example title="defaults">
                <recently-created-repositories />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="LandingSearchBox">
            <component-showcase-example title="defaults">
                <landing-search-box />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="LandingInfoSections">
            <component-showcase-example title="defaults">
                <landing-info-sections />
            </component-showcase-example>
        </component-showcase>
    </page-container>
</template>
