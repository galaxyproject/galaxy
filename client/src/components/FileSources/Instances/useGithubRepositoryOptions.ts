import { computed, type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { GithubRepository } from "@/api/configTemplates";
import type { FileSourceTemplateSummary } from "@/api/fileSources";
import type { DynamicOptions, SelectFormOption } from "@/components/ConfigTemplates/formUtil";
import { errorMessageAsString } from "@/utils/simple-error";

// Markers a github template's `org`/`repo` select variables declare via `dynamic_options`.
// The owner dropdown lists the distinct owners of the authorized repositories; the repo
// dropdown is filtered to the repositories of the currently selected owner.
const OWNERS_MARKER = "github_repository_owners";
const NAMES_MARKER = "github_repository_names";

/**
 * Populate the `org`/`repo` dropdowns of a GitHub file source create form with the repositories
 * the user authorized the GitHub App to access.
 *
 * Fetches the authorized repositories once (after the OAuth return, when `uuid` is defined) and
 * exposes a reactive `dynamicOptions` map keyed by variable name. The repo options depend on the
 * owner currently selected in `formData`, so picking an owner filters the repositories.
 */
export function useGithubRepositoryOptions(
    template: Ref<FileSourceTemplateSummary>,
    uuid: Ref<string | undefined>,
    formData: Ref<Record<string, unknown>>,
) {
    const repositories = ref<GithubRepository[]>([]);
    const loading = ref(false);
    const error = ref<string | null>(null);
    // Whether a repository fetch has actually completed (guards the empty-state message so it is
    // not shown before the post-OAuth fetch resolves).
    const fetched = ref(false);

    const ownerVariableName = computed(() => findVariableByMarker(template.value, OWNERS_MARKER));
    const repoVariableName = computed(() => findVariableByMarker(template.value, NAMES_MARKER));
    const isRepositoryPicker = computed(() => Boolean(ownerVariableName.value && repoVariableName.value));

    const currentOwner = computed<string | undefined>(() => {
        const name = ownerVariableName.value;
        const value = name ? formData.value?.[name] : undefined;
        return typeof value === "string" ? value : undefined;
    });

    const ownerOptions = computed<SelectFormOption[]>(() => {
        const owners = Array.from(new Set(repositories.value.map((repository) => repository.owner)));
        return owners.map((owner): SelectFormOption => [owner, owner]);
    });

    const repoOptions = computed<SelectFormOption[]>(() => {
        const owner = currentOwner.value;
        if (!owner) {
            return [];
        }
        return repositories.value
            .filter((repository) => repository.owner === owner)
            .map((repository): SelectFormOption => [repository.repo, repository.repo]);
    });

    const dynamicOptions = computed<DynamicOptions>(() => {
        const options: DynamicOptions = {};
        if (!isRepositoryPicker.value) {
            return options;
        }
        if (ownerVariableName.value) {
            options[ownerVariableName.value] = ownerOptions.value;
        }
        if (repoVariableName.value) {
            options[repoVariableName.value] = repoOptions.value;
        }
        return options;
    });

    // True once the picker fetched but the GitHub App granted access to no repositories, so the
    // owner/repo dropdowns are empty. The user must install the App on a repository first.
    const noRepositoriesFound = computed(
        () =>
            isRepositoryPicker.value &&
            fetched.value &&
            !loading.value &&
            !error.value &&
            repositories.value.length === 0,
    );

    async function fetchRepositories() {
        if (!isRepositoryPicker.value || !uuid.value) {
            return;
        }
        loading.value = true;
        error.value = null;
        try {
            const { data, error: requestError } = await GalaxyApi().GET(
                "/api/file_source_templates/{template_id}/{template_version}/repositories",
                {
                    params: {
                        path: {
                            template_id: template.value.id,
                            template_version: template.value.version ?? 0,
                        },
                        query: { uuid: uuid.value },
                    },
                },
            );
            if (requestError) {
                error.value = errorMessageAsString(requestError);
            } else {
                repositories.value = data ?? [];
            }
        } catch (e) {
            error.value = errorMessageAsString(e);
        } finally {
            loading.value = false;
            fetched.value = true;
        }
    }

    watch([uuid, isRepositoryPicker], () => void fetchRepositories(), { immediate: true });

    return { dynamicOptions, loading, error, isRepositoryPicker, noRepositoriesFound };
}

function findVariableByMarker(template: FileSourceTemplateSummary, marker: string): string | undefined {
    for (const variable of template.variables ?? []) {
        if (variable.type === "select" && variable.dynamic_options === marker) {
            return variable.name;
        }
    }
    return undefined;
}
