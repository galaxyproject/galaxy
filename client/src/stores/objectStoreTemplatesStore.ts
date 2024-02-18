import { defineStore } from "pinia";

import { fetcher } from "@/api/schema/fetcher";
import type { components } from "@/api/schema/schema";
import { errorMessageAsString } from "@/utils/simple-error";

const getObjectStoreTemplates = fetcher.path("/api/object_store_templates").method("get").create();

type ObjectStoreTemplateSummary = components["schemas"]["ObjectStoreTemplateSummary"];
type ObjectStoreTemplateSummaries = ObjectStoreTemplateSummary[];

function findTemplate(templates: ObjectStoreTemplateSummaries, templateId: string, templateVersion: number) {
    for (const template of templates) {
        if (template.id == templateId && template.version == templateVersion) {
            return template;
        }
    }
    return null;
}

function getLatestVersionMap(templates: ObjectStoreTemplateSummaries): { [key: string]: number } {
    const latestVersions: { [key: string]: number } = {};
    templates.forEach((i: ObjectStoreTemplateSummary) => {
        const templateId = i.id;
        const templateVersion = i.version || 0;
        if ((latestVersions[templateId] ?? -1) < templateVersion) {
            latestVersions[templateId] = templateVersion;
        }
    });
    return latestVersions;
}

function canUpgrade(templates: ObjectStoreTemplateSummaries, templateId: string, templateVersion: number): boolean {
    let can = false;
    templates.forEach((i: ObjectStoreTemplateSummary) => {
        if (i.id == templateId && i.version && i.version > templateVersion) {
            can = true;
        }
    });
    return can;
}

function getLatestVersion(templates: ObjectStoreTemplateSummaries, id: string): ObjectStoreTemplateSummary | null {
    let latestVersion = -1;
    let latestTemplate = null as ObjectStoreTemplateSummary | null;
    templates.forEach((i: ObjectStoreTemplateSummary) => {
        const templateId = i.id;
        if (templateId == id) {
            const templateVersion = i.version || 0;
            if (templateVersion > latestVersion) {
                latestTemplate = i;
                latestVersion = templateVersion;
            }
        }
    });
    return latestTemplate;
}

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
