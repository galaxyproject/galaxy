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
    const alertConditions = ref<string[]>([]);
    const error = ref<string | null>(null);

    const variables = computed(() => {
        const values: Record<string, string | number | boolean> = {};
        for (const variable of template.value.variables ?? []) {
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
            error.value = errorMessageAsString(requestError);
            return;
        }
        // openapi-fetch widens the server's [label, value] tuples to string[][]; they are
        // pairs by construction, so narrow them back to SelectFormOption tuples here.
        dynamicOptions.value = (data.dynamic_options ?? {}) as DynamicOptions;
        alertConditions.value = data.alert_conditions ?? [];
    }

    watch([uuid, variables], () => void fetchFormData(), { immediate: true });

    return { alertConditions, dynamicOptions, error };
}
