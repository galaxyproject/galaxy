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

// MetadataInspector components
import ChangesetSummaryTable from "@/components/MetadataInspector/ChangesetSummaryTable.vue"
import JsonDiffViewer from "@/components/MetadataInspector/JsonDiffViewer.vue"
import MetadataJsonViewer from "@/components/MetadataInspector/MetadataJsonViewer.vue"
import RevisionsTab from "@/components/MetadataInspector/RevisionsTab.vue"
import OverviewTab from "@/components/MetadataInspector/OverviewTab.vue"
import ToolHistoryTab from "@/components/MetadataInspector/ToolHistoryTab.vue"

// Fixtures for MetadataInspector demos
import {
    repositoryMetadataColumnMaker,
    repositoryMetadataBismark,
    resetMetadataPreview,
    resetMetadataBismark,
    resetMetadataUnchanged,
    resetMetadataSubset,
    getChangesetDetails,
    getFirstRevision,
    makeChangeset,
    type RepositoryMetadata,
} from "@/components/MetadataInspector/__fixtures__"

// Prepared demo data - all comparison result types
const changesetsAllResults = [
    makeChangeset({
        numeric_revision: 0,
        comparison_result: "initial",
        record_operation: null,
        changeset_revision: "abc1234567890",
    }),
    makeChangeset({
        numeric_revision: 1,
        comparison_result: "not equal and not subset",
        record_operation: "created",
        changeset_revision: "def2345678901",
    }),
    makeChangeset({
        numeric_revision: 2,
        comparison_result: "not equal and not subset",
        record_operation: "updated",
        changeset_revision: "ghi3456789012",
    }),
    makeChangeset({
        numeric_revision: 3,
        comparison_result: "equal",
        record_operation: null,
        changeset_revision: "jkl4567890123",
    }),
    makeChangeset({
        numeric_revision: 4,
        comparison_result: "subset",
        record_operation: null,
        has_tools: false,
        changeset_revision: "mno5678901234",
    }),
    makeChangeset({
        numeric_revision: 5,
        comparison_result: null,
        record_operation: null,
        has_tools: false,
        error: "Failed to parse tool XML: invalid syntax at line 42",
        changeset_revision: "pqr6789012345",
    }),
]

const changesetsFromColumnMaker = getChangesetDetails(resetMetadataPreview)
const changesetsFromBismark = getChangesetDetails(resetMetadataBismark)
const changesetsFromUnchanged = getChangesetDetails(resetMetadataUnchanged)
const changesetsFromSubset = getChangesetDetails(resetMetadataSubset)

const sampleRevisionData = getFirstRevision(repositoryMetadataColumnMaker)

// JSON diff examples
const diffBefore = { name: "my_tool", version: "1.0.0", description: "Old description" }
const diffAfter = { name: "my_tool", version: "1.1.0", description: "New improved description", author: "dev" }
const diffIdentical = { name: "unchanged", version: "1.0.0" }

// Single revision for simpler demos
const singleRevisionMetadata: RepositoryMetadata = (() => {
    const keys = Object.keys(repositoryMetadataColumnMaker)
    return { [keys[0]]: repositoryMetadataColumnMaker[keys[0]] }
})()
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

        <!-- MetadataInspector Components -->
        <div class="text-h5 q-my-lg">MetadataInspector Components</div>

        <component-showcase title="ChangesetSummaryTable">
            <component-showcase-example
                title="simulated: all comparison results"
                description="Programmatically generated to show all possible comparison_result values"
            >
                <ChangesetSummaryTable :changesets="changesetsAllResults" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example
                title="column_maker (API fixture)"
                description="Real API response from column_maker test repo - 3 revisions with tools"
            >
                <ChangesetSummaryTable :changesets="changesetsFromColumnMaker" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example
                title="bismark (API fixture)"
                description="Real API response from bismark test repo - has tool dependencies and invalid_tools"
            >
                <ChangesetSummaryTable :changesets="changesetsFromBismark" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example
                title="unchanged revisions (API fixture)"
                description="Real API response showing 'Unchanged' change type - identical tool metadata between revisions"
            >
                <ChangesetSummaryTable :changesets="changesetsFromUnchanged" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example
                title="subset (API fixture)"
                description="Real API response showing 'Additive' change type - new tool added without modifying existing"
            >
                <ChangesetSummaryTable :changesets="changesetsFromSubset" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="empty" description="No changesets">
                <ChangesetSummaryTable :changesets="[]" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="JsonDiffViewer">
            <component-showcase-example title="with changes (added, modified)">
                <JsonDiffViewer :before="diffBefore" :after="diffAfter" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="no changes">
                <JsonDiffViewer :before="diffIdentical" :after="diffIdentical" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="complex metadata diff">
                <JsonDiffViewer
                    :before="resetMetadataPreview.repository_metadata_before"
                    :after="resetMetadataPreview.repository_metadata_after"
                />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="MetadataJsonViewer">
            <component-showcase-example title="revision metadata with tooltips">
                <MetadataJsonViewer
                    v-if="sampleRevisionData"
                    :data="sampleRevisionData"
                    model-name="RepositoryRevisionMetadata"
                />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="collapsed (deep=1)">
                <MetadataJsonViewer v-if="sampleRevisionData" :data="sampleRevisionData" :deep="1" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="expanded (deep=4)">
                <MetadataJsonViewer v-if="sampleRevisionData" :data="sampleRevisionData" :deep="4" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="RevisionsTab">
            <component-showcase-example title="multi-revision repo (column_maker)">
                <RevisionsTab :metadata="repositoryMetadataColumnMaker" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="with invalid tools (bismark)">
                <RevisionsTab :metadata="repositoryMetadataBismark" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="empty metadata">
                <RevisionsTab :metadata="null" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="OverviewTab">
            <component-showcase-example title="with revision selector">
                <OverviewTab :metadata="repositoryMetadataColumnMaker" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="single revision">
                <OverviewTab :metadata="singleRevisionMetadata" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="no metadata">
                <OverviewTab :metadata="null" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="ToolHistoryTab">
            <component-showcase-example title="tool version timeline">
                <ToolHistoryTab :metadata="repositoryMetadataColumnMaker" />
            </component-showcase-example>
            <q-separator />
            <component-showcase-example title="no tools">
                <ToolHistoryTab :metadata="null" />
            </component-showcase-example>
        </component-showcase>
    </page-container>
</template>
