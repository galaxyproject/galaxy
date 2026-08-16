import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import { parseBlockContent, serializeBlockContent } from "./blockContent";

describe("blockContent", () => {
    it("parses JSON verbatim (YAML is a superset)", () => {
        expect(parseBlockContent('{"visualization_name":"igv","dataset_id":"d1"}')).toEqual({
            visualization_name: "igv",
            dataset_id: "d1",
        });
    });

    it("parses YAML", () => {
        expect(parseBlockContent("visualization_name: igv\ndataset_id: d1")).toEqual({
            visualization_name: "igv",
            dataset_id: "d1",
        });
    });

    it("returns an empty object for empty content", () => {
        expect(parseBlockContent("")).toEqual({});
    });

    it("serializes to YAML that round-trips", () => {
        const value = { visualization_name: "igv", tracks: [{ dataset_id: "d1" }] };
        const yaml = serializeBlockContent(value);
        expect(yaml).not.toContain("{");
        expect(parse(yaml)).toEqual(value);
    });

    it("preserves author key order rather than alphabetizing", () => {
        const yaml = serializeBlockContent({ zebra: 1, apple: 2 });
        expect(yaml.indexOf("zebra")).toBeLessThan(yaml.indexOf("apple"));
    });
});
