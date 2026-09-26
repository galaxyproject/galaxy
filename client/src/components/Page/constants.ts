/**
 * Centralized user-facing strings for pages/notebooks/reports.
 *
 * Backend uses "page" everywhere — that's an implementation detail.
 * Frontend terminology:
 *   - "Galaxy Notebook" — history-attached pages (the working document)
 *   - "Report"          — standalone pages (the publishable artifact)
 *
 * Change strings here to rename across the entire UI.
 */
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faBook, faFileContract } from "@fortawesome/free-solid-svg-icons";

import type { PageEditorMode } from "@/stores/pageEditorStore";

/** Per-mode labels used by the page editor, history page list, chat panel, etc. */
export const PAGE_LABELS: Record<
    PageEditorMode,
    {
        entityName: string;
        entityNamePlural: string;
        titleIcon: IconDefinition;
        defaultTitle: string;
        editorBackLabel: string;
        newButton: string;
        emptyStateTitle: string;
        emptyStateDescription: string;
        editButton: string;
        viewButton: string;
        createButton: string;
        historyCounterTooltip?: string;
    }
> = {
    history: {
        entityName: "Galaxy Notebook",
        entityNamePlural: "Galaxy Notebooks",
        titleIcon: faBook,
        defaultTitle: "Untitled Notebook",
        editorBackLabel: "This History's Notebooks",
        newButton: "New Notebook",
        emptyStateTitle: "No notebooks yet",
        emptyStateDescription:
            "Create a notebook to document your analysis with rich markdown, embedded datasets, and visualizations.",
        editButton: "Edit Notebook",
        viewButton: "View Notebook",
        createButton: "Create Notebook",
        historyCounterTooltip: "Galaxy Notebooks",
    },
    standalone: {
        entityName: "Report",
        entityNamePlural: "Reports",
        titleIcon: faFileContract,
        defaultTitle: "Untitled Report",
        editorBackLabel: "Back to Reports",
        newButton: "Create Report",
        emptyStateTitle: "No reports yet",
        emptyStateDescription: "Create a report to publish your analysis.",
        editButton: "Edit Report",
        viewButton: "View Report",
        createButton: "Create Report",
    },
    invocation: {
        entityName: "Invocation Report",
        entityNamePlural: "Invocation Reports",
        titleIcon: faFileContract,
        defaultTitle: "Untitled Invocation Report",
        editorBackLabel: "This Invocation's Reports",
        newButton: "New Invocation Report",
        emptyStateTitle: "No invocation reports yet",
        emptyStateDescription:
            "Create a report in the form of a Galaxy Notebook to document this workflow invocation with rich markdown, embedded datasets, and visualizations.",
        editButton: "Edit Invocation Report",
        viewButton: "View Invocation Report",
        createButton: "Create Invocation Report",
    },
} as const;

/** Grid page (lists standalone reports). */
export const GRID_LABELS = {
    heading: "Reports",
    createButton: "Create Report",
    myTab: "My Reports",
    publicTab: "Public Reports",
    loginRequired: "Manage your Reports",
    savedTitle: "Saved Reports",
    publishedTitle: "Published Reports",
    gridPlural: "Reports",
    deleteConfirm: "Are you sure that you want to delete the selected report?",
    restoreConfirm: "Are you sure that you want to restore the selected report?",
    windowTitle: (title: unknown) => `Report: ${title}`,
} as const;

/** Activity bar entry. */
export const ACTIVITY_LABELS = {
    title: "Reports",
    description: "Display and create new reports.",
    tooltip: "Show all reports",
} as const;

/** Agent type registry. */
export const AGENT_LABELS = {
    pageAssistantLabel: "Markdown Assistant",
    pageAssistantDescription: "Markdown editing assistant",
} as const;

/** Error messages (store) — generic since they apply to both types. */
export const ERROR_MESSAGES = {
    loadList: "Failed to load pages",
    loadPage: "Failed to load page",
    createPage: "Failed to create page",
    savePage: "Failed to save page",
    deletePage: "Failed to delete page",
    loadRevisions: "Failed to load revisions",
    loadRevision: "Failed to load revision",
    restoreRevision: "Failed to restore revision",
} as const;

/** Published page view. */
export const PUBLISHED_LABELS = {
    editButton: "Edit Report",
    loadingMessage: "Loading Report",
    errorHeading: "Failed to load Report",
    modelClass: "Report",
} as const;

/** Page form (create/edit standalone reports). */
export const FORM_LABELS = {
    createTitle: "Create a new Report",
    editTitle: "Edit Report",
    slugHelp:
        "A unique identifier that will be used for public links to this report. " +
        "This field can only contain lowercase letters, numbers, and dashes (-).",
    annotationHelp: "A description of the report. The annotation is shown alongside published reports.",
} as const;

/** Embed labels. */
export const EMBED_LABELS = {
    iframeTitle: "Galaxy Report Embed",
    showTitle: "Show report title",
} as const;

/** Object permissions modal. */
export const PERMISSIONS_LABELS = {
    modalTitle: "Report Object Permissions",
} as const;
