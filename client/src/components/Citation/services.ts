import axios from "axios";

import { useConfig } from "@/composables/config";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import type { Citation } from ".";

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
        // Inject Galaxy citation from config, using Cite for formatting
        const { config } = useConfig();
        let galaxyCitation = null;
        const galaxy_bibtex = config.value?.citation_bibtex;
        if (galaxy_bibtex) {
            try {
                const cite = new Cite(galaxy_bibtex);
                galaxyCitation = { raw: galaxy_bibtex, cite };
            } catch (err) {
                console.warn("Error parsing Galaxy BibTeX:", err);
            }
        }
        return galaxyCitation ? [galaxyCitation, ...citations] : citations;
    } catch (e) {
        rethrowSimple(e);
    }
}
