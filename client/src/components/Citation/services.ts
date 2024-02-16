import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import { type Citation } from ".";

export async function getCitations(source: string, id: string): Promise<Citation[]> {
    try {
        const request = await axios.get(`${getAppRoot()}api/${source}/${id}/citations`);
        const rawCitations = request.data;
        const citations = [];
        const { Cite } = await import(/* webpackChunkName: "cite" */ "./cite");
        for (const rawCitation of rawCitations) {
            try {
                const cite = new Cite(rawCitation.content);
                citations.push({ raw: rawCitation.content, cite: cite });
            } catch (err) {
                console.warn(`Error parsing bibtex: ${err}`);
            }
        }
        return citations;
    } catch (e) {
        rethrowSimple(e);
    }
}
