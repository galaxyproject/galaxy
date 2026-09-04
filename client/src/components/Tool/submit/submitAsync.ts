import { GalaxyApi } from "@/api";
import { fetchJobOutputs, type JobRequest, submitJobRequest } from "@/api/jobs";
import type { ToolFormConfig, ToolRequestDetailedModel } from "@/api/tools";
import { buildNestedState } from "@/components/Form/utilities";
import { pollUntil } from "@/composables/pollUntil";
import { rethrowSimple } from "@/utils/simple-error";

export async function submitToolJob({
    jobDef,
    formConfig,
    formData,
}: {
    jobDef: JobRequest;
    formConfig: ToolFormConfig;
    formData: FormData;
}) {
    const nestedInputs = buildNestedState(formConfig.inputs, formData);
    const request = { ...jobDef, inputs: nestedInputs as Record<string, unknown> };
    const { tool_request_id } = await submitJobRequest(request);
    const detail = await waitForToolRequest(tool_request_id);
    return buildJobResponse(detail);
}

async function waitForToolRequest(toolRequestId: string, { pollInterval = 1000, timeout = 600000 } = {}) {
    const terminalState = await pollUntil({
        fn: async () => {
            const { data, error } = await GalaxyApi().GET("/api/tool_requests/{id}/state", {
                params: { path: { id: toolRequestId } },
            });
            if (error) {
                rethrowSimple(error);
            }
            return data;
        },
        condition: (state) => state !== "new",
        interval: pollInterval,
        timeout,
    });

    const { data: detail, error: detailError } = await GalaxyApi().GET("/api/tool_requests/{id}", {
        params: { path: { id: toolRequestId } },
    });
    if (detailError) {
        rethrowSimple(detailError);
    }

    if (terminalState === "failed") {
        const stateMessage = detail.state_message;
        const error = Object.assign(new Error(stateMessage?.err_msg || "Tool request failed"), {
            err_data: stateMessage?.err_data,
            err_msg: stateMessage?.err_msg,
        });
        throw error;
    }

    return detail;
}

async function buildJobResponse(toolRequestDetail: ToolRequestDetailedModel) {
    const jobs = toolRequestDetail.jobs.map((j) => ({ id: j.id }));
    const allJobOutputs = await Promise.all(jobs.map((j) => fetchJobOutputs(j.id)));
    const datasetFetches = [];
    const collectionFetches = [];

    for (const jobOutputs of allJobOutputs) {
        for (const out of jobOutputs) {
            if ("dataset" in out && out.dataset) {
                datasetFetches.push(
                    GalaxyApi()
                        .GET("/api/datasets/{dataset_id}", {
                            params: { path: { dataset_id: out.dataset.id } },
                        })
                        .then(({ data, error }) => {
                            if (error) {
                                rethrowSimple(error);
                            }
                            // TODO: The dataset response is not modeled yet in the FastAPI route for /api/datasets/{dataset_id}
                            const dataset = data as { hid: number; name: string };
                            return {
                                hid: dataset.hid,
                                name: dataset.name,
                            };
                        }),
                );
            }
            if ("dataset_collection_instance" in out && out.dataset_collection_instance) {
                collectionFetches.push(
                    GalaxyApi()
                        .GET("/api/dataset_collections/{hdca_id}", {
                            params: { path: { hdca_id: out.dataset_collection_instance.id } },
                        })
                        .then(({ data, error }) => {
                            if (error) {
                                rethrowSimple(error);
                            }
                            return { hid: data.hid, name: data.name };
                        }),
                );
            }
        }
    }

    const [outputs, output_collections] = await Promise.all([
        Promise.all(datasetFetches),
        Promise.all(collectionFetches),
    ]);

    return {
        jobs,
        outputs,
        output_collections,
    };
}
