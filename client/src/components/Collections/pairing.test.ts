import { guessInitialFilterType, guessNameForPair } from "./pairing";

describe("guessInitialFilterType", () => {
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

function mockDataset(name: string) {
    return { name };
}

describe("guessNameForPair", () => {
    test("it should use the LCS and work with _1/_2 filters", () => {
        expect(guessNameForPair(mockDataset("moo_1.fastq"), mockDataset("moo_2.fastq"), "_1", "_2", true)).toEqual(
            "moo"
        );
    });

    test("it should use the LCS as a name and work with .1.fastq/.2.fastq filters", () => {
        expect(
            guessNameForPair(mockDataset("moo.1.fastq"), mockDataset("moo.2.fastq"), ".1.fastq", ".2.fastq", true)
        ).toEqual("moo");
    });

    test("it should use the LCS as a name and part of that is cutting out mismatched junk", () => {
        expect(
            guessNameForPair(
                mockDataset("moo_middledifferent_endssame.1.fastq"),
                mockDataset("moo_yuck_endssame.2.fastq"),
                ".1.fastq",
                ".2.fastq",
                true
            )
        ).toEqual("moo__endssame");
    });

    /* The way the filters and extension stripping are handled is less than ideal, this should work IMO for instance. -jmchilton
    test("it should use the LCS as a name and part of that is cutting out mismatched junk", () => {
        expect(guessNameForPair(mockDataset("moo.middledifferent.endssame.1.fastq"), mockDataset("moo.yuck.endssame.2.fastq"), ".1.fastq", ".2.fastq", true)).toEqual("moo.endssame");
    });
    */
});
