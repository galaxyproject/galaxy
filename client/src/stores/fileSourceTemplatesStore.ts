import { defineStore } from "pinia";

import { type components, GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import { canUpgrade, findTemplate, getLatestVersion, getLatestVersionMap } from "./configTemplatesUtil";

type FileSourceTemplateSummary = components["schemas"]["FileSourceTemplateSummary"];
type FileSourceTemplateSummaries = FileSourceTemplateSummary[];

export const useFileSourceTemplatesStore = defineStore("fileSourceTemplatesStore", {
    state: () => ({
        templates: [] as FileSourceTemplateSummaries,
        fetched: false,
        error: null as string | null,
    }),
    getters: {
        latestTemplates: (state) => {
            // only expose latest instance by template_version for each template_id
            const latestVersions = getLatestVersionMap(state.templates);
            return state.templates.filter((i: FileSourceTemplateSummary) => latestVersions[i.id] == (i.version || 0));
        },
        canUpgrade: (state) => {
            return (templateId: string, templateVersion: number) =>
                canUpgrade(state.templates, templateId, templateVersion);
        },
        getTemplates: (state) => {
            return state.templates;
        },
        getTemplate: (state) => {
            return (templateId: string, templateVersion: number) =>
                findTemplate(state.templates, templateId, templateVersion);
        },
        getLatestTemplate: (state) => {
            return (templateId: string) => getLatestVersion(state.templates, templateId);
        },
        hasTemplates: (state) => {
            return state.templates.length > 0;
        },
        loading: (state) => {
            return !state.fetched;
        },
    },
    actions: {
        async handleInit(templates: FileSourceTemplateSummaries) {
            this.templates = templates;
            this.fetched = true;
        },
        async handleError(err: unknown) {
            this.fetched = true;
            this.error = errorMessageAsString(err);
        },
        async fetchTemplates() {
            const { data: templates, error } = await GalaxyApi().GET("/api/file_source_templates");

            if (error) {
                this.handleError(error);
                return;
            }

            this.handleInit(templates);
        },
        async ensureTemplates() {
            if (!this.fetched || this.error != null) {
                await this.fetchTemplates();
            }
        },
    },
});
