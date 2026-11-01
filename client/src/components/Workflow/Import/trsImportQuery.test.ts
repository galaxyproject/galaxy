import { describe, expect, it } from "vitest";

import { trsImportQuery } from "./trsImportQuery";

describe("trsImportQuery", () => {
    it("reads the version from trs_version, as GTN and Dockstore launch links send it", () => {
        const query = trsImportQuery({
            trs_server: "dockstore.org",
            trs_id: "#workflow/github.com/org/repo/main",
            trs_version: "v0.1.3",
            run_form: "true",
        });
        expect(query).toEqual({
            trsId: "#workflow/github.com/org/repo/main",
            trsUrl: undefined,
            trsServer: "dockstore.org",
            trsVersionId: "v0.1.3",
            isRun: true,
        });
    });

    it("still accepts trs_version_id", () => {
        expect(trsImportQuery({ trs_version_id: "main" }).trsVersionId).toBe("main");
    });

    it("is not a run without run_form=true", () => {
        expect(trsImportQuery({}).isRun).toBe(false);
    });
});
