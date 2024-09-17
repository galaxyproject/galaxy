import {
    type CreateInstancePayload,
    type Instance,
    type PluginStatus,
    type SecretData,
    type TemplateSecret,
    type TemplateSummary,
    type TemplateVariable,
    type VariableData,
    type VariableValueType,
} from "@/api/configTemplates";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

export interface FormEntry {
    name: string;
    label?: string;
    optional?: boolean;
    help?: string | null;
    type: string;
    value?: any;
}

export function metadataFormEntryName(what: string): FormEntry {
    return {
        name: "_meta_name",
        label: "Name",
        type: "text",
        optional: false,
        help: `Label this new ${what} with a name.`,
    };
}

export function metadataFormEntryDescription(what: string): FormEntry {
    return {
        name: "_meta_description",
        label: "Description",
        optional: true,
        type: "textarea",
        help: `Provide some notes to yourself about this ${what} - perhaps to remind you how it is configured, where it stores the data, etc..`,
    };
}

export function templateVariableFormEntry(variable: TemplateVariable, variableValue?: VariableValueType): FormEntry {
    const common_fields = {
        name: variable.name,
        label: variable.label ?? variable.name,
        help: markup(variable.help || "", true),
    };
    if (variable.type == "string") {
        const defaultValue = variable.default ?? "";
        return {
            type: "text",
            value: variableValue == undefined ? defaultValue : variableValue,
            ...common_fields,
        };
    } else if (variable.type == "path_component") {
        const defaultValue = variable.default ?? "";
        // TODO: do extra validation with form somehow...
        return {
            type: "text",
            value: variableValue == undefined ? defaultValue : variableValue,
            ...common_fields,
        };
    } else if (variable.type == "integer") {
        const defaultValue = variable.default ?? 0;
        return {
            type: "integer",
            value: variableValue == undefined ? defaultValue : variableValue,
            ...common_fields,
        };
    } else if (variable.type == "boolean") {
        const defaultValue = variable.default ?? false;
        return {
            type: "boolean",
            value: variableValue == undefined ? defaultValue : variableValue,
            ...common_fields,
        };
    } else {
        throw Error("Invalid template form input type found.");
    }
}

export function templateSecretFormEntry(secret: TemplateSecret): FormEntry {
    return {
        name: secret.name,
        label: secret.label ?? secret.name,
        type: "password",
        help: markup(secret.help || "", true),
        value: "",
    };
}

export function editTemplateForm(template: TemplateSummary, what: string, instance: Instance): FormEntry[] {
    const form = [];
    const nameInput = metadataFormEntryName(what);
    form.push({ value: instance.name ?? "", ...nameInput });

    const descriptionInput = metadataFormEntryDescription(what);
    form.push({ value: instance.description ?? "", ...descriptionInput });

    const variables = template.variables ?? [];
    const variableValues: VariableData = instance.variables || {};
    for (const variable of variables) {
        form.push(templateVariableFormEntry(variable, variableValues[variable.name]));
    }
    return form;
}

export function editFormDataToPayload(template: TemplateSummary, formData: any) {
    const variables = template.variables ?? [];
    const name = formData["_meta_name"];
    const description = formData["_meta_description"];
    const variableData: VariableData = {};
    for (const variable of variables) {
        const variableValue = formDataTypedGet(variable, formData);
        if (variableValue !== undefined) {
            variableData[variable.name] = variableValue;
        }
    }
    const payload = {
        name: name,
        description: description,
        variables: variableData,
    };
    return payload;
}

export function createTemplateForm(template: TemplateSummary, what: string): FormEntry[] {
    const form = [];
    const variables = template.variables ?? [];
    const secrets = template.secrets ?? [];
    form.push(metadataFormEntryName(what));
    form.push(metadataFormEntryDescription(what));
    for (const variable of variables) {
        form.push(templateVariableFormEntry(variable, undefined));
    }
    for (const secret of secrets) {
        form.push(templateSecretFormEntry(secret));
    }
    return form;
}

export function createFormDataToPayload(template: TemplateSummary, formData: any): CreateInstancePayload {
    const variables = template.variables ?? [];
    const secrets = template.secrets ?? [];
    const variableData: VariableData = {};
    const secretData: SecretData = {};
    for (const variable of variables) {
        const variableValue = formDataTypedGet(variable, formData);
        if (variableValue !== undefined) {
            variableData[variable.name] = variableValue;
        }
    }
    for (const secret of secrets) {
        secretData[secret.name] = formData[secret.name];
    }
    const name: string = formData._meta_name;
    const description: string = formData._meta_description;
    const payload: CreateInstancePayload = {
        name: name,
        description: description,
        secrets: secretData,
        variables: variableData,
        template_id: template.id,
        template_version: template.version ?? 0,
    };
    return payload;
}

export function formDataTypedGet(variableDefinition: TemplateVariable, formData: any): VariableValueType | undefined {
    // galaxy form library doesn't type values traditionally, so add a typed
    // access to the data if coming back as string. Though it does seem to be
    // typed properly - this might not be needed anymore?
    const variableType = variableDefinition.type;
    const variableName = variableDefinition.name;
    const rawValue: boolean | string | number | null | undefined = formData[variableName];
    if (variableType == "string") {
        if (rawValue == null || rawValue == undefined) {
            return undefined;
        } else {
            return String(rawValue);
        }
    } else if (variableType == "path_component") {
        if (rawValue == null || rawValue == undefined) {
            return undefined;
        } else {
            return String(rawValue);
        }
    } else if (variableType == "boolean") {
        if (rawValue == null || rawValue == undefined || typeof rawValue == "number") {
            return undefined;
        } else {
            return String(rawValue).toLowerCase() == "true";
        }
    } else if (variableType == "integer") {
        if (rawValue == null || rawValue == undefined || typeof rawValue == "boolean") {
            return undefined;
        } else {
            if (typeof rawValue == "string") {
                return parseInt(rawValue);
            } else {
                return rawValue;
            }
        }
    } else {
        throw Error("Unknown variable type encountered, shouldn't be possible.");
    }
}

export function upgradeForm(template: TemplateSummary, instance: Instance): FormEntry[] {
    const form = [];
    const variables = template.variables ?? [];
    const secrets = template.secrets ?? [];
    const variableValues: VariableData = instance.variables || {};
    const secretsSet = instance.secrets || [];
    for (const variable of variables) {
        form.push(templateVariableFormEntry(variable, variableValues[variable.name]));
    }
    for (const secret of secrets) {
        const secretName = secret.name;
        if (secretsSet.indexOf(secretName) >= 0) {
            console.log("skipping...");
        } else {
            form.push(templateSecretFormEntry(secret));
        }
    }
    return form;
}

export function upgradeFormDataToPayload(template: TemplateSummary, formData: any) {
    const variables = template.variables ?? [];
    const variableData: VariableData = {};
    for (const variable of variables) {
        variableData[variable.name] = formData[variable.name];
    }
    const secrets = {};
    // ideally we would be able to force a template version here,
    // maybe rework backend types to force this in the API response
    // even if we don't need it in the config files
    const templateVersion: number = template.version || 0;
    const payload = {
        template_version: templateVersion,
        variables: variableData,
        secrets: secrets,
    };
    return payload;
}

export function pluginStatusToErrorMessage(pluginStatus: PluginStatus): string | null {
    if (pluginStatus.template_definition.state == "not_ok") {
        return pluginStatus.template_definition.message;
    } else if (pluginStatus.template_settings?.state == "not_ok") {
        return pluginStatus.template_settings.message;
    } else if (pluginStatus.connection?.state == "not_ok") {
        return pluginStatus.connection.message;
    }
    return null;
}
