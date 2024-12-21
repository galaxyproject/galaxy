import { guessInitialFilterType } from "./pairing";

describe("guessInitialFilterType", () => {
    beforeEach(() => {});

    test("should return 'illumina' when illumina matches are most common", () => {
        const elements = [
            { name: "sample1_1.fastq" },
            { name: "sample1_2.fastq" },
            { name: "sample2_1.fastq" },
            { name: "sample2_2.fastq" },
        ];
        expect(guessInitialFilterType(elements)).toBe("illumina");
    });

    test("should return 'null' when none of the filters work well", () => {
        const elements = [{ name: "mydata123.fastq" }, { name: "mydata124.fastq" }, { name: "mydata125.fastq" }];
        expect(guessInitialFilterType(elements)).toBe(null);
    });
});
