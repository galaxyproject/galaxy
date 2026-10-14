import { getFakePageDetails } from "@tests/test-data/pages";

import { http } from "@/api/client/__mocks__/http";

/** A standalone notebook its author published. */
export const PUBLISHED_PAGE = getFakePageDetails({
    id: "f2db41a1fa331b3e",
    history_id: null,
    title: "Yeast heat-shock RNA-seq",
    slug: "yeast-heat-shock-rna-seq",
    published: true,
    importable: true,
    username: "jdoe",
    content: "## Methods\n\nReads were trimmed with Cutadapt and aligned with HISAT2.",
    content_editor: "## Methods\n\nReads were trimmed with Cutadapt and aligned with HISAT2.",
});

/** Answers `GET /api/pages/{id}` with `page`. */
export function pageHandler(page = PUBLISHED_PAGE) {
    return http.get("/api/pages/{id}", ({ response }) => response(200).json(page));
}
