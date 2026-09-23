/**
 * Example usage of the Galaxy API client
 *
 * These examples demonstrate common operations using the Galaxy API.
 * All examples use openapi-fetch's typed client for full type safety.
 */
import { createGalaxyApi } from "./index";

// =============================================================================
// CLIENT SETUP EXAMPLES
// =============================================================================

// Basic usage - just provide a base URL
const basicApi = createGalaxyApi("https://usegalaxy.org");

// With API key authentication
const authenticatedApi = createGalaxyApi({
    baseUrl: "https://usegalaxy.org",
    apiKey: "your-api-key-here",
});

// With custom headers and fetch options
const _customApi = createGalaxyApi({
    baseUrl: "https://usegalaxy.org",
    apiKey: "your-api-key-here",
    headers: {
        "User-Agent": "MyGalaxyApp/1.0",
    },
    fetchOptions: {
        credentials: "include",
    },
});

// =============================================================================
// HISTORY EXAMPLES
// =============================================================================

/**
 * List all histories for the current user
 */
async function listHistories() {
    const { data, error } = await authenticatedApi.GET("/api/histories");

    if (error) {
        console.error("Error fetching histories:", error);
        return [];
    }

    console.log(`Found ${data.length} histories:`);
    for (const history of data) {
        console.log(`  - ${history.name} (${history.id})`);
    }

    return data;
}

/**
 * Get the most recently used history
 */
async function getMostRecentHistory() {
    const { data, error } = await authenticatedApi.GET("/api/histories/most_recently_used");

    if (error) {
        console.error("Error fetching most recent history:", error);
        return null;
    }

    console.log(`Most recent history: ${data.name}`);
    return data;
}

/**
 * Get detailed information about a specific history
 */
async function getHistoryDetails(historyId: string) {
    const { data, error } = await authenticatedApi.GET("/api/histories/{history_id}", {
        params: {
            path: { history_id: historyId },
        },
    });

    if (error) {
        console.error("Error fetching history details:", error);
        return null;
    }

    console.log(`History: ${data.name} (${data.id})`);
    return data;
}

/**
 * Update a history's name or annotation
 */
async function updateHistory(historyId: string, updates: { name?: string; annotation?: string }) {
    const { data, error } = await authenticatedApi.PUT("/api/histories/{history_id}", {
        params: {
            path: { history_id: historyId },
        },
        body: updates,
    });

    if (error) {
        console.error("Error updating history:", error);
        return null;
    }

    console.log(`Updated history: ${data.name}`);
    return data;
}

/**
 * Delete a history (moves to trash)
 */
async function deleteHistory(historyId: string, purge = false) {
    const { data, error } = await authenticatedApi.DELETE("/api/histories/{history_id}", {
        params: {
            path: { history_id: historyId },
            query: { purge },
        },
    });

    if (error) {
        console.error("Error deleting history:", error);
        return null;
    }

    console.log(`Deleted history: ${historyId}`);
    return data;
}

/**
 * Get published (public) histories
 */
async function getPublishedHistories() {
    const { data, error } = await basicApi.GET("/api/histories/published");

    if (error) {
        console.error("Error fetching published histories:", error);
        return [];
    }

    console.log(`Found ${data.length} published histories`);
    return data;
}

// =============================================================================
// DATASET EXAMPLES
// =============================================================================

/**
 * Get details about a specific dataset in a history
 */
async function getDatasetDetails(historyId: string, datasetId: string) {
    const { data, error } = await authenticatedApi.GET("/api/histories/{history_id}/contents/{type}s/{id}", {
        params: {
            path: {
                history_id: historyId,
                type: "dataset",
                id: datasetId,
            },
        },
    });

    if (error) {
        console.error("Error fetching dataset:", error);
        return null;
    }

    console.log(`Dataset: ${data.name}`);
    return data;
}

// =============================================================================
// JOB EXAMPLES
// =============================================================================

/**
 * Get job status and details
 */
async function getJobStatus(jobId: string) {
    const { data, error } = await authenticatedApi.GET("/api/jobs/{job_id}", {
        params: {
            path: { job_id: jobId },
        },
    });

    if (error) {
        console.error("Error fetching job:", error);
        return null;
    }

    console.log(`Job ${jobId}: ${data.state}`);
    return data;
}

// =============================================================================
// WORKFLOW EXAMPLES
// =============================================================================

/**
 * List all workflows accessible to the user
 */
async function listWorkflows() {
    const { data, error } = await authenticatedApi.GET("/api/workflows");

    if (error) {
        console.error("Error fetching workflows:", error);
        return [];
    }

    console.log(`Found ${data.length} workflows`);
    return data;
}

/**
 * Get workflow details
 */
async function getWorkflowDetails(workflowId: string) {
    const { data, error } = await authenticatedApi.GET("/api/workflows/{workflow_id}", {
        params: {
            path: { workflow_id: workflowId },
        },
    });

    if (error) {
        console.error("Error fetching workflow:", error);
        return null;
    }

    console.log(`Workflow: ${data.name}`);
    return data;
}

// =============================================================================
// INVOCATION EXAMPLES
// =============================================================================

/**
 * Get workflow invocation status
 */
async function getInvocationStatus(invocationId: string) {
    const { data, error } = await authenticatedApi.GET("/api/invocations/{invocation_id}", {
        params: {
            path: { invocation_id: invocationId },
        },
    });

    if (error) {
        console.error("Error fetching invocation:", error);
        return null;
    }

    console.log(`Invocation ${invocationId}: ${data.state}`);
    return data;
}

// =============================================================================
// EXPORTS
// =============================================================================

export {
    // History operations
    listHistories,
    getMostRecentHistory,
    getHistoryDetails,
    updateHistory,
    deleteHistory,
    getPublishedHistories,
    // Dataset operations
    getDatasetDetails,
    // Job operations
    getJobStatus,
    // Workflow operations
    listWorkflows,
    getWorkflowDetails,
    // Invocation operations
    getInvocationStatus,
};
