import { defineStore } from "pinia";

import { fetcher } from "@/api/schema/fetcher";
import { type components } from "@/api/schema/schema";
import { errorMessageAsString } from "@/utils/simple-error";

import { canUpgrade, findTemplate, getLatestVersion, getLatestVersionMap } from "./configTemplatesUtil";

const getObjectStoreTemplates = fetcher.path("/api/object_store_templates").method("get").create();

type ObjectStoreTemplateSummary = components["schemas"]["ObjectStoreTemplateSummary"];
type ObjectStoreTemplateSummaries = ObjectStoreTemplateSummary[];

export const useObjectStoreTemplatesStore = defineStore("objectStoreTemplatesStore", {
    state: () => ({
        templates: [] as ObjectStoreTemplateSummaries,
        fetched: false,
        error: null as string | null,
    }),
    getters: {
        latestTemplates: (state) => {
            // only expose latest instance by template_version for each template_id
            const latestVersions = getLatestVersionMap(state.templates);
            return state.templates.filter((i: ObjectStoreTemplateSummary) => latestVersions[i.id] == (i.version || 0));
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
        async handleInit(templates: ObjectStoreTemplateSummaries) {
            this.templates = templates;
            this.fetched = true;
        },
        async handleError(err: unknown) {
            this.fetched = true;
            this.error = errorMessageAsString(err);
        },
        async fetchTemplates() {
            try {
                const { data: templates } = await getObjectStoreTemplates({});
                this.handleInit(templates);
            } catch (err) {
                this.handleError(err);
            }
        },
        async ensureTemplates() {
            if (!this.fetched || this.error != null) {
                await this.fetchTemplates();
            }
        },
    },
});
