import axios from "axios";

import { GalaxyApi } from "@/api";
import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export type Workflow = Record<string, never>;

type SortBy = "create_time" | "update_time" | "name";

interface LoadWorkflowsOptions {
    sortBy: SortBy;
    sortDesc: boolean;
    limit: number;
    offset: number;
    filterText: string;
    showPublished: boolean;
    skipStepCounts: boolean;
}

export async function loadWorkflows({
    sortBy = "update_time",
    sortDesc = true,
    limit = 20,
    offset = 0,
    filterText = "",
    showPublished = false,
    skipStepCounts = true,
}: LoadWorkflowsOptions): Promise<{ data: Workflow[]; totalMatches: number }> {
    const { response, data, error } = await GalaxyApi().GET("/api/workflows", {
        params: {
            query: {
                sort_by: sortBy,
                sort_desc: sortDesc,
                limit,
                offset,
                search: filterText,
                show_published: showPublished,
                skip_step_counts: skipStepCounts,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    const totalMatches = parseInt(response.headers.get("Total_matches") || "0", 10) || 0;

    return { data, totalMatches };
}

export async function updateWorkflow(id: string, changes: object): Promise<Workflow> {
    const { data } = await axios.put(withPrefix(`/api/workflows/${id}`), changes);
    return data;
}

export async function copyWorkflow(id: string, currentOwner: string, version?: string): Promise<Workflow> {
    let path = `/api/workflows/${id}/download`;
    if (version) {
        path += `?version=${version}`;
    }
    const { data: workflowData } = await axios.get(withPrefix(path));

    workflowData.name = `Copy of ${workflowData.name}`;
    const userStore = useUserStore();

    if (!userStore.matchesCurrentUsername(currentOwner)) {
        workflowData.name += ` shared by user ${currentOwner}`;
    }

    const { data } = await axios.post(withPrefix("/api/workflows"), { workflow: workflowData });
    return data;
}

export async function deleteWorkflow(id: string): Promise<Workflow> {
    const { data } = await axios.delete(withPrefix(`/api/workflows/${id}`));
    return data;
}

export async function undeleteWorkflow(id: string): Promise<Workflow> {
    const { data } = await axios.post(withPrefix(`/api/workflows/${id}/undelete`));
    return data;
}

export async function createWorkflow(workflowName: string, workflowAnnotation: string) {
    const { data } = await axios.put(withPrefix("/workflow/create"), {
        workflow_name: workflowName,
        workflow_annotation: workflowAnnotation,
    });
    return data;
}

export async function getWorkflowFull(workflowId: string, version?: number) {
    let url = `/workflow/load_workflow?_=true&id=${workflowId}`;
    if (version !== undefined) {
        url += `&version=${version}`;
    }
    const { data } = await axios.get(withPrefix(url));
    return data;
}

export async function getWorkflowInfo(workflowId: string) {
    const { data } = await axios.get(withPrefix(`/api/workflows/${workflowId}`));
    return data;
}

/**
 * For dockstore imported IWC workflows, fetch the README file from the GitHub repository.
 * @param trsId of form `#workflow/github.com/iwc-workflows/<directory>/...`
 * @param versionId optional version tag (uses `main` branch if not provided)
 * @returns the README and CHANGELOG file contents
 */
export async function fetchDocsForIwcWorkflow(trsId: string, versionId?: string) {
    // Ensure that the trsID is for a GitHub workflow at iwc-workflows
    const parts = trsId.split("/");
    if (parts.length !== 5 || parts[0] !== "#workflow" || parts[1] !== "github.com" || parts[2] !== "iwc-workflows") {
        return { readme: null, changelog: null };
    }

    const directory = parts[3];

    // Construct the URL for the README and CHANGELOG files
    let baseUrl = `https://raw.githubusercontent.com/iwc-workflows/${directory}/refs/`;
    if (!versionId) {
        baseUrl += "heads/main/";
    } else {
        baseUrl += `tags/${versionId}/`;
    }
    try {
        // Fetch the files
        const [readmeResponse, changelogResponse] = await Promise.all([
            fetch(baseUrl + "README.md"),
            fetch(baseUrl + "CHANGELOG.md"),
        ]);

        const readme = readmeResponse.ok ? await readmeResponse.text() : null;
        const changelog = changelogResponse.ok ? await changelogResponse.text() : null;

        return {
            /**The README.md of the workflow fetched from the IWC GitHub repository */
            readme,
            /** The CHANGELOG.md of the workflow fetched from the IWC GitHub repository */
            changelog,
        };
    } catch (error) {
        rethrowSimple(error);
    }
}
