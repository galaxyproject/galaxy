/**
 * Centralized user-facing strings for pages/notebooks/reports.
 *
 * Backend uses "page" everywhere — that's an implementation detail.
 * Frontend terminology:
 *   - "Galaxy Notebook"   — history-attached pages (the working document)
 *   - "Notebook"          — standalone pages (the publishable artifact)
 *   - "Invocation Report" — pages generated for a workflow invocation
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
        entityName: "Notebook",
        entityNamePlural: "Notebooks",
        titleIcon: faFileContract,
        defaultTitle: "Untitled Notebook",
        editorBackLabel: "Back to Notebooks",
        newButton: "Create Notebook",
        emptyStateTitle: "No notebooks yet",
        emptyStateDescription: "Create a notebook to publish your analysis.",
        editButton: "Edit Notebook",
        viewButton: "View Notebook",
        createButton: "Create Notebook",
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

/** Grid page (lists standalone notebooks). */
export const GRID_LABELS = {
    heading: "Notebooks",
    createButton: "Create Notebook",
    myTab: "My Notebooks",
    publicTab: "Public Notebooks",
    loginRequired: "Manage your Notebooks",
    savedTitle: "Saved Notebooks",
    publishedTitle: "Published Notebooks",
    gridPlural: "Notebooks",
    deleteConfirm: "Are you sure that you want to delete the selected notebook?",
    restoreConfirm: "Are you sure that you want to restore the selected notebook?",
    windowTitle: (title: unknown) => `Notebook: ${title}`,
} as const;

/** Activity bar entry. */
export const ACTIVITY_LABELS = {
    title: "Notebooks",
    description: "Display and create new notebooks.",
    tooltip: "Show all notebooks",
} as const;

/** Agent type registry. */
export const AGENT_LABELS = {
    pageAssistantLabel: "Markdown Assistant",
    pageAssistantDescription: "Markdown editing assistant",
} as const;

/** Error messages (store) — generic since they apply to both types. */
export const ERROR_MESSAGES = {
    loadList: "Failed to load notebooks",
    loadPage: "Failed to load notebook",
    createPage: "Failed to create notebook",
    savePage: "Failed to save notebook",
    deletePage: "Failed to delete notebook",
    loadRevisions: "Failed to load revisions",
    loadRevision: "Failed to load revision",
    restoreRevision: "Failed to restore revision",
} as const;

/** Published page view. */
export const PUBLISHED_LABELS = {
    editButton: "Edit Notebook",
    loadingMessage: "Loading Notebook",
    errorHeading: "Failed to load Notebook",
    modelClass: "Notebook",
} as const;

/** Page form (create/edit standalone notebooks). */
export const FORM_LABELS = {
    createTitle: "Create a new Notebook",
    editTitle: "Edit Notebook",
    slugHelp:
        "A unique identifier that will be used for public links to this notebook. " +
        "This field can only contain lowercase letters, numbers, and dashes (-).",
    annotationHelp: "A description of the notebook. The annotation is shown alongside published notebooks.",
} as const;

/** Embed labels. */
export const EMBED_LABELS = {
    iframeTitle: "Galaxy Notebook Embed",
    showTitle: "Show notebook title",
} as const;

/** Object permissions modal. */
export const PERMISSIONS_LABELS = {
    modalTitle: "Notebook Object Permissions",
} as const;
