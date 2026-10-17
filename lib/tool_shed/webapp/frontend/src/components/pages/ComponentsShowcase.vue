<script setup lang="ts">
import PageContainer from "@/components/PageContainer.vue"
import LoadingDiv from "@/components/LoadingDiv.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import ComponentShowcase from "@/components/ComponentShowcase.vue"
import ComponentShowcaseExample from "@/components/ComponentShowcaseExample.vue"
import { GButton, GCheckbox, GHeading, GLink, useToast } from "@galaxyproject/galaxy-ui"
import RecentlyCreatedRepositories from "@/components/RecentlyCreatedRepositories.vue"
import RepositoryLink from "@/components/RepositoryLink.vue"
import RepositoryActions from "@/components/RepositoryActions.vue"
import LandingSearchBox from "@/components/LandingSearchBox.vue"
import LandingInfoSections from "@/components/LandingInfoSections.vue"
import RepositoryFileTree from "@/components/RepositoryFileTree.vue"
import RepositoryFileViewer from "@/components/RepositoryFileViewer.vue"
import RepositoryContentsBrowser from "@/components/RepositoryContentsBrowser.vue"
import { newestRevision, type RepositoryFileContents, type RepositoryFileEntry } from "@/api"
import { ref } from "vue"

const { addToast } = useToast()

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
    resetMetadataDirectPush,
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
const changesetsFromDirectPush = getChangesetDetails(resetMetadataDirectPush)

const sampleRevisionData = getFirstRevision(repositoryMetadataColumnMaker)

// JSON diff examples
const diffBefore = { name: "my_tool", version: "1.0.0", description: "Old description" }
const diffAfter = { name: "my_tool", version: "1.1.0", description: "New improved description", author: "dev" }
const diffIdentical = { name: "unchanged", version: "1.0.0" }

// Repository file browser demos
function fileEntry(path: string, type: RepositoryFileEntry["type"] = "file"): RepositoryFileEntry {
    return { path, size: 1024, type, executable: false }
}
const demoFiles: RepositoryFileEntry[] = [
    fileEntry("column_maker/column_maker.xml"),
    fileEntry("column_maker/column_maker.py"),
    fileEntry("column_maker/test-data/bed_file.bed"),
    fileEntry("column_maker/test-data/a_file_with_a_really_long_name_that_needs_to_wrap_somewhere.tabular"),
    fileEntry("column_maker/macros.xml", "symlink"),
    fileEntry(".shed.yml"),
    fileEntry("README.rst"),
]
const selectedDemoFile = ref<string | null>("column_maker/test-data/bed_file.bed")
function demoContents(overrides: Partial<RepositoryFileContents> = {}): RepositoryFileContents {
    return {
        path: "column_maker/column_maker.xml",
        size: 120,
        type: "file",
        binary: false,
        truncated: false,
        content:
            '<tool id="Add_a_column1" name="Compute" version="1.3.0">\n    <description>on rows</description>\n</tool>\n',
        ...overrides,
    }
}

const browserRevision = ref(newestRevision(repositoryMetadataColumnMaker))
const browserFile = ref<string | null>("column_maker/column_maker.xml")

// Single revision for simpler demos
const singleRevisionMetadata: RepositoryMetadata = (() => {
    const keys = Object.keys(repositoryMetadataColumnMaker)
    return { [keys[0]]: repositoryMetadataColumnMaker[keys[0]] }
})()
</script>

<template>
    <page-container>
        This page is only meant for tool shed developers. It demonstrates common widgets and styles in isolation.

        <component-showcase title="Galaxy UI (galaxy-ui package)">
            <component-showcase-example title="GButton colors">
                <GButton color="blue">Blue</GButton>
                <GButton color="green">Green</GButton>
                <GButton color="red">Red</GButton>
                <GButton>Default</GButton>
            </component-showcase-example>
            <hr />
            <component-showcase-example title="GButton variants">
                <GButton color="blue" outline>Outline</GButton>
                <GButton color="blue" transparent>Transparent</GButton>
                <GButton color="blue" pill>Pill</GButton>
                <GButton color="blue" disabled disabled-title="Disabled example">Disabled</GButton>
            </component-showcase-example>
            <hr />
            <component-showcase-example title="GButton sizes">
                <GButton color="blue" size="small">Small</GButton>
                <GButton color="blue" size="medium">Medium</GButton>
                <GButton color="blue" size="large">Large</GButton>
            </component-showcase-example>
            <hr />
            <component-showcase-example title="GHeading">
                <GHeading h2 size="md" separator>Section heading</GHeading>
            </component-showcase-example>
            <hr />
            <component-showcase-example title="GLink">
                <GLink href="https://galaxyproject.org">External link</GLink>
            </component-showcase-example>
            <hr />
            <component-showcase-example title="GCheckbox">
                <GCheckbox>Labeled checkbox</GCheckbox>
            </component-showcase-example>
            <hr />
            <component-showcase-example title="Toasts (notify)">
                <GButton color="green" @click="addToast('Repository saved', { variant: 'success' })">Success</GButton>
                <GButton color="blue" @click="addToast('Indexing started', { variant: 'info' })">Info</GButton>
                <GButton color="orange" @click="addToast('Revision is outdated', { variant: 'warning' })">
                    Warning
                </GButton>
                <GButton color="red" @click="addToast('Request failed', { variant: 'danger' })">Error</GButton>
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="LoadingDiv">
            <component-showcase-example title="default">
                <loading-div />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="with supplied message">
                <loading-div message="I'm loading" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="ErrorBanner">
            <component-showcase-example title="default error message">
                <error-banner error="My Cool Error Message" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="long error message">
                <error-banner
                    error="This is a very long error message that might wrap or cause layout issues in the UI, but should still be displayed correctly to the user with proper formatting and readability."
                />
            </component-showcase-example>
            <hr />
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

        <component-showcase title="RepositoryFileTree">
            <component-showcase-example title="nested folders, a symlink and a selected file">
                <RepositoryFileTree
                    :files="demoFiles"
                    :selected="selectedDemoFile"
                    @select="selectedDemoFile = $event"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="nothing selected">
                <RepositoryFileTree :files="demoFiles" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="RepositoryFileViewer">
            <component-showcase-example title="text file">
                <RepositoryFileViewer :file="demoContents()" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="long lines scroll">
                <RepositoryFileViewer
                    :file="demoContents({ path: 'test-data/wide.tabular', content: 'column\t'.repeat(60) })"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="binary">
                <RepositoryFileViewer
                    :file="demoContents({ path: 'test-data/input.bam', binary: true, content: null })"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="too large">
                <RepositoryFileViewer
                    :file="demoContents({ path: 'test-data/big.fasta', truncated: true, size: 5242880, content: null })"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="symbolic link">
                <RepositoryFileViewer :file="demoContents({ path: 'macros.xml', type: 'symlink', content: null })" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="empty file">
                <RepositoryFileViewer :file="demoContents({ path: 'test-data/empty.txt', size: 0, content: '' })" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="loading">
                <RepositoryFileViewer :file="null" loading />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="error">
                <RepositoryFileViewer :file="null" error="Request failed with status 404: No such file" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="nothing selected">
                <RepositoryFileViewer :file="null" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="RepositoryContentsBrowser">
            <component-showcase-example title="browsing a file">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    :revision="browserRevision"
                    :files="demoFiles"
                    :file="browserFile"
                    :contents="demoContents({ path: browserFile ?? '' })"
                    @update:revision="browserRevision = $event"
                    @select="browserFile = $event"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="no file selected">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    :revision="browserRevision"
                    :files="demoFiles"
                    :contents="null"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="files loading">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    :revision="browserRevision"
                    :files="null"
                    files-loading
                    :contents="null"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="file listing failed">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    :revision="browserRevision"
                    :files="null"
                    files-error="Failed to load the files in this revision."
                    :contents="null"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="revision with no files">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    :revision="browserRevision"
                    :files="[]"
                    :contents="null"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="file not in this revision">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    :revision="browserRevision"
                    :files="demoFiles"
                    file="tool_removed_later.xml"
                    file-missing
                    :contents="null"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="revision is not installable">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    revision="0123456789ab"
                    revision-unavailable
                    :files="null"
                    :contents="null"
                />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="no installable revisions">
                <RepositoryContentsBrowser :revisions="{}" :revision="null" :files="null" :contents="null" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="deprecated repository">
                <RepositoryContentsBrowser
                    :revisions="repositoryMetadataColumnMaker"
                    :revision="browserRevision"
                    withdrawn="deprecated"
                    :files="null"
                    :contents="null"
                />
            </component-showcase-example>
        </component-showcase>

        <!-- MetadataInspector Components -->
        <h2 class="metadata-inspector-heading">MetadataInspector Components</h2>

        <component-showcase title="ChangesetSummaryTable">
            <component-showcase-example
                title="simulated: all comparison results"
                description="Programmatically generated to show all possible comparison_result values"
            >
                <ChangesetSummaryTable :changesets="changesetsAllResults" />
            </component-showcase-example>
            <hr />
            <component-showcase-example
                title="column_maker (API fixture)"
                description="Real API response from column_maker test repo - 3 revisions with tools"
            >
                <ChangesetSummaryTable :changesets="changesetsFromColumnMaker" />
            </component-showcase-example>
            <hr />
            <component-showcase-example
                title="bismark (API fixture)"
                description="Real API response from bismark test repo - has tool dependencies and invalid_tools"
            >
                <ChangesetSummaryTable :changesets="changesetsFromBismark" />
            </component-showcase-example>
            <hr />
            <component-showcase-example
                title="unchanged revisions (API fixture)"
                description="Real API response showing 'Unchanged' change type - identical tool metadata between revisions"
            >
                <ChangesetSummaryTable :changesets="changesetsFromUnchanged" />
            </component-showcase-example>
            <hr />
            <component-showcase-example
                title="subset (API fixture)"
                description="Real API response showing 'Additive' change type - new tool added without modifying existing"
            >
                <ChangesetSummaryTable :changesets="changesetsFromSubset" />
            </component-showcase-example>
            <hr />
            <component-showcase-example
                title="direct push (API fixture)"
                description="Real API response showing 'New Record' operation - changeset pushed via hg without metadata"
            >
                <ChangesetSummaryTable :changesets="changesetsFromDirectPush" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="empty" description="No changesets">
                <ChangesetSummaryTable :changesets="[]" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="JsonDiffViewer">
            <component-showcase-example title="with changes (added, modified)">
                <JsonDiffViewer :before="diffBefore" :after="diffAfter" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="no changes">
                <JsonDiffViewer :before="diffIdentical" :after="diffIdentical" />
            </component-showcase-example>
            <hr />
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
            <hr />
            <component-showcase-example title="collapsed (deep=1)">
                <MetadataJsonViewer v-if="sampleRevisionData" :data="sampleRevisionData" :deep="1" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="expanded (deep=4)">
                <MetadataJsonViewer v-if="sampleRevisionData" :data="sampleRevisionData" :deep="4" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="RevisionsTab">
            <component-showcase-example title="multi-revision repo (column_maker)">
                <RevisionsTab :metadata="repositoryMetadataColumnMaker" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="with invalid tools (bismark)">
                <RevisionsTab :metadata="repositoryMetadataBismark" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="empty metadata">
                <RevisionsTab :metadata="null" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="OverviewTab">
            <component-showcase-example title="with revision selector">
                <OverviewTab :metadata="repositoryMetadataColumnMaker" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="single revision">
                <OverviewTab :metadata="singleRevisionMetadata" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="no metadata">
                <OverviewTab :metadata="null" />
            </component-showcase-example>
        </component-showcase>

        <component-showcase title="ToolHistoryTab">
            <component-showcase-example title="single tool with version history (column_maker)">
                <ToolHistoryTab :metadata="repositoryMetadataColumnMaker" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="multiple different tools (bismark)">
                <ToolHistoryTab :metadata="repositoryMetadataBismark" />
            </component-showcase-example>
            <hr />
            <component-showcase-example title="no tools">
                <ToolHistoryTab :metadata="null" />
            </component-showcase-example>
        </component-showcase>
    </page-container>
</template>

<style scoped>
.metadata-inspector-heading {
    margin-top: var(--spacing-6);
    margin-bottom: var(--spacing-6);
    font-size: 1.5rem;
}
</style>
