import { type TemplateSummary } from "@/api/configTemplates";

export function findTemplate<T extends TemplateSummary>(
    templates: T[],
    templateId: string,
    templateVersion: number
): T | null {
    for (const template of templates) {
        if (template.id == templateId && template.version == templateVersion) {
            return template;
        }
    }
    return null;
}

export function getLatestVersionMap<T extends TemplateSummary>(templates: T[]): { [key: string]: number } {
    const latestVersions: { [key: string]: number } = {};
    templates.forEach((i: T) => {
        const templateId = i.id;
        const templateVersion = i.version || 0;
        if ((latestVersions[templateId] ?? -1) < templateVersion) {
            latestVersions[templateId] = templateVersion;
        }
    });
    return latestVersions;
}

export function canUpgrade<T extends TemplateSummary>(
    templates: T[],
    templateId: string,
    templateVersion: number
): boolean {
    let can = false;
    templates.forEach((i: T) => {
        if (i.id == templateId && i.version && i.version > templateVersion) {
            can = true;
        }
    });
    return can;
}

export function getLatestVersion<T extends TemplateSummary>(templates: T[], id: string): T | null {
    let latestVersion = -1;
    let latestTemplate = null as T | null;
    templates.forEach((i: T) => {
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
