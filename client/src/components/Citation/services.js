import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function getCitations(source, id) {
    try {
        const request = await axios.get(`${getAppRoot()}api/${source}/${id}/citations`);
        const rawCitations = request.data;
        const citations = [];
        import(/* webpackChunkName: "CitationJS" */ "citation-js").then(({ default: Cite }) => {
            for (const rawCitation of rawCitations) {
                try {
                    const cite = new Cite(rawCitation.content);
                    citations.push({ raw: rawCitation.content, cite: cite });
                } catch (err) {
                    console.warn(`Error parsing bibtex: ${err}`);
                }
            }
        });
        return citations;
    } catch (e) {
        rethrowSimple(e);
    }
}
