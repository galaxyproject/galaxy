import { computed, type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { FileSourceTemplateSummary } from "@/api/fileSources";
import type { DynamicOptions } from "@/components/ConfigTemplates/formUtil";
import { errorMessageAsString } from "@/utils/simple-error";

/** Fetch server-supplied options and UI conditions for a post-authorization template form. */
export function useTemplateFormData(
    template: Ref<FileSourceTemplateSummary>,
    uuid: Ref<string | undefined>,
    formData: Ref<Record<string, unknown>>,
) {
    const dynamicOptions = ref<DynamicOptions>({});
    const messages = ref<
        Array<{
            content: string;
            variant: "primary" | "secondary" | "success" | "danger" | "warning" | "info" | "light" | "dark";
        }>
    >([]);
    const error = ref<string | null>(null);
    let requestSequence = 0;

    const variables = computed(() => {
        const values: Record<string, string | number | boolean> = {};
        const dependencies = new Set(
            (template.value.variables ?? []).flatMap((variable) =>
                variable.type === "select" ? (variable.options_provider?.depends_on ?? []) : [],
            ),
        );
        for (const variable of template.value.variables ?? []) {
            if (!dependencies.has(variable.name)) {
                continue;
            }
            const value = formData.value[variable.name];
            if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
                values[variable.name] = value;
            }
        }
        return values;
    });

    async function fetchFormData() {
        if (!uuid.value) {
            return;
        }
        const sequence = ++requestSequence;
        error.value = null;
        const { data, error: requestError } = await GalaxyApi().POST(
            "/api/file_source_templates/{template_id}/{template_version}/form-data",
            {
                params: {
                    path: { template_id: template.value.id, template_version: template.value.version ?? 0 },
                },
                body: { uuid: uuid.value, variables: variables.value },
            },
        );
        if (requestError) {
            if (sequence === requestSequence) {
                error.value = errorMessageAsString(requestError);
            }
            return;
        }
        if (sequence !== requestSequence) {
            return;
        }
        // openapi-fetch widens the server's [label, value] tuples to string[][]; they are
        // pairs by construction, so narrow them back to SelectFormOption tuples here.
        dynamicOptions.value = (data.dynamic_options ?? {}) as DynamicOptions;
        messages.value = data.messages ?? [];
    }

    watch([uuid, variables], () => void fetchFormData(), { immediate: true });

    return { dynamicOptions, error, messages };
}
