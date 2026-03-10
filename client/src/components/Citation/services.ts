import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import type { CitationsResult } from ".";

export async function getCitations(source: string, id: string): Promise<CitationsResult> {
    try {
        const request = await axios.get(`${getAppRoot()}api/${source}/${id}/citations`);
        const rawCitations = request.data;
        const citations = [];
        const warnings: string[] = [];
        const { Cite } = await import("./cite");
        for (const rawCitation of rawCitations) {
            if (rawCitation.format === "error") {
                warnings.push(rawCitation.error);
                continue;
            }
            try {
                const cite = new Cite(rawCitation.content);
                citations.push({ raw: rawCitation.content, cite: cite });
            } catch (err) {
                console.warn(`Error parsing bibtex: ${err}`);
            }
        }
        return { citations, warnings };
    } catch (e) {
        rethrowSimple(e);
    }
}
