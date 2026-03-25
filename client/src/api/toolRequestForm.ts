import { GalaxyApi } from "@/api";
import type { components } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

export type ToolRequestFormData = components["schemas"]["ToolRequestFormData"];

export async function submitToolRequest(payload: ToolRequestFormData): Promise<void> {
    const { error } = await GalaxyApi().POST("/api/tool_request_form", { body: payload });
    if (error) {
        rethrowSimple(error);
    }
}
