// Vitest test for Citation component

import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { getCitations } from "./services";

const { server, http } = useServerMock();

const mockCitationResponseJson = [
    {
        format: "bibtex",
        content:
            "@article{Hourahine_2020,\n\tdoi = {10.1063/1.5143190},\n\turl = {https://doi.org/10.1063%2F1.5143190},\n\tyear = 2020,\n\tmonth = {mar},\n\tpublisher = {{AIP} Publishing},\n\tvolume = {152},\n\tnumber = {12},\n\tpages = {124101},\n\tauthor = {B. Hourahine and B. Aradi and V. Blum and F. Bonaf{\\'{e}} and A. Buccheri and C. Camacho and C. Cevallos and M. Y. Deshaye and T. Dumitric{\\u{a}} and A. Dominguez and S. Ehlert and M. Elstner and T. van der Heide and J. Hermann and S. Irle and J. J. Kranz and C. K\u00f6hler and T. Kowalczyk and T. Kuba{\\v{r}} and I. S. Lee and V. Lutsker and R. J. Maurer and S. K. Min and I. Mitchell and C. Negre and T. A. Niehaus and A. M. N. Niklasson and A. J. Page and A. Pecchia and G. Penazzi and M. P. Persson and J. {\\v{R}}ez{\\'{a}}{\\v{c}} and C. G. S{\\'{a}}nchez and M. Sternberg and M. St\u00f6hr and F. Stuckenberg and A. Tkatchenko and V. W.-z. Yu and T. Frauenheim},\n\ttitle = {{DFTB}$\\mathplus$, a software package for efficient approximate density functional theory based atomistic simulations},\n\tjournal = {The Journal of Chemical Physics}\n}",
    },
];

describe("Citation", () => {
    describe("services", () => {
        it("Should fetch and create a citation object", async () => {
            server.use(
                http.untyped.get("/api/tools/random_lines1/citations", () => {
                    return HttpResponse.json(mockCitationResponseJson);
                }),
            );
            const result = await getCitations("tools", "random_lines1");
            expect(result.warnings).toHaveLength(0);
            const formattedCitation = result.citations?.[0]?.cite.format("bibliography", {
                format: "html",
                template: "apa",
                lang: "en-US",
            });
            expect(formattedCitation).toContain("Hourahine");
            // TODO: actually test formatting here, too.
        });

        it("Should separate error entries into warnings", async () => {
            const mockResponseWithErrors = [
                ...mockCitationResponseJson,
                {
                    format: "error",
                    error: "Tool 'missing_tool' not found. Citations for this tool may be missing.",
                    tool_id: "missing_tool",
                },
            ];
            server.use(
                http.untyped.get("/api/histories/test-history/citations", () => {
                    return HttpResponse.json(mockResponseWithErrors);
                }),
            );
            const result = await getCitations("histories", "test-history");
            expect(result.citations).toHaveLength(1);
            expect(result.warnings).toHaveLength(1);
            expect(result.warnings[0]).toContain("missing_tool");
        });
    });
});
