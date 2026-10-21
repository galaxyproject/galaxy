import { HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";
import type { PredictedToolChild } from "@/components/Workflow/Editor/modules/utilities";

// The shipped cat1 tool inherits its output format; Cut1 accepts text and is named "Cut".
export const PREDICTIONS = {
    current_tool: "cat1",
    predicted_data: {
        name: "Concatenate multiple datasets or collections",
        is_deprecated: false,
        o_extensions: ["input"],
        children: [
            { name: "Cut", tool_id: "Cut1", tool_score: 0.9, i_extensions: ["txt"] },
        ] satisfies PredictedToolChild[],
    },
};

/** This legacy endpoint is not part of Galaxy's OpenAPI schema. */
export function toolPredictions(predictions: typeof PREDICTIONS) {
    return http.untyped.post("/api/workflows/get_tool_predictions", async ({ request }) => {
        const payload = (await request.json()) as { tool_sequence?: string };
        if (payload.tool_sequence === predictions.current_tool) {
            return HttpResponse.json(predictions);
        }
    });
}
