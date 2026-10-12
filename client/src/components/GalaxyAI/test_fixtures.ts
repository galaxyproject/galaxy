import type { components } from "@/api";
import { http } from "@/api/client/__mocks__/http";

type ChatResponse = components["schemas"]["ChatResponse"];

/** The exchange Galaxy saves a new conversation under. */
export const NEW_EXCHANGE_ID = "5f2c4e8a91b07d36";

/** GalaxyAI's answer to a question about read mappers. */
export const MAPPER_ANSWER = "For short reads against a reference genome, BWA-MEM2 and Bowtie2 are good choices.";

/** A successful `POST /api/chat` answer, saved under `exchangeId`. */
export function chatResponse(response: string, exchangeId: string): ChatResponse {
    return { response, exchange_id: exchangeId, error_code: 0, error_message: "", processing_time: 1.2 };
}

/**
 * Answers every question with `answer`, as Galaxy does: under the conversation's exchange, or a new
 * one for a conversation not saved yet.
 */
export function chatAnswers(answer: string) {
    return http.post("/api/chat", async ({ request, response }) => {
        const { exchange_id } = (await request.json()) ?? {};
        return response(200).json(chatResponse(answer, exchange_id ?? NEW_EXCHANGE_ID));
    });
}

/** The router asks this when a request could mean a tool suggestion or a lesson. */
export const CLARIFICATION_QUESTION = "Do you want a tool recommendation or a tutorial?";

/** The router's documented quick-reply choices; omitted for a free-text clarification. */
export const CLARIFICATION_OPTIONS = ["Tool recommendation", "Tutorial"];
