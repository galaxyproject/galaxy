import { GalaxyApi } from "@/api";
import { type HDADetailed } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

export async function submitReport(
    reportableData: HDADetailed,
    message: string,
    email: string
): Promise<{ messages: string[][]; error?: string }> {
    try {
        const { data, error } = await GalaxyApi().POST("/api/jobs/{job_id}/error", {
            params: {
                path: { job_id: reportableData.creating_job },
            },
            body: {
                dataset_id: reportableData.id,
                message,
                email,
            },
        });

        if (error) {
            return { messages: [], error: errorMessageAsString(error) };
        }
        return { messages: data.messages };
    } catch (err) {
        return { messages: [], error: errorMessageAsString(err) };
    }
}
