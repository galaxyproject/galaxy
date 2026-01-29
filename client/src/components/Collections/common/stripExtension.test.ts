import { stripExtension } from "./stripExtension";

describe("stripExtension", () => {
    test("strips single extensions", () => {
        expect(stripExtension("sample.fastq")).toBe("sample");
        expect(stripExtension("data.bam")).toBe("data");
        expect(stripExtension("example.fasta")).toBe("example");
        expect(stripExtension("sample.txt")).toBe("sample");
    });

    test("strips multi-part extensions with secondary extensions", () => {
        expect(stripExtension("sample.fastq.gz")).toBe("sample");
        expect(stripExtension("data.fasta.tgz")).toBe("data");
        expect(stripExtension("example.bam.bz2")).toBe("example");
    });

    test("handles filenames with multiple dots", () => {
        expect(stripExtension("my.sample.fastq.gz")).toBe("my.sample");
        expect(stripExtension("test.data.vcf.gz")).toBe("test.data");
        expect(stripExtension("dataset.v1.bam.bz2")).toBe("dataset.v1");
    });

    test("preserves filenames without dots", () => {
        expect(stripExtension("no_extension")).toBe("no_extension");
    });

    test("tries to avoid significant metadata that might look like an extension", () => {
        expect(stripExtension("mycondition1.mysample1234")).toBe("mycondition1.mysample1234");
        expect(stripExtension("mycondition1.mysample1234.fastq")).toBe("mycondition1.mysample1234");
        expect(stripExtension("mycondition1.mysample1234.fastq.gz")).toBe("mycondition1.mysample1234");
    });

    test("handles edge cases", () => {
        expect(stripExtension(".fastq.gz")).toBe("");
        expect(stripExtension("file..fastq.gz")).toBe("file.");
        expect(stripExtension("file.fastq.extra.gz")).toBe("file.fastq");
    });
});
