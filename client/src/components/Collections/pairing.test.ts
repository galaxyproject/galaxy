import AUTO_PAIRING_SPECIFICATION from "./auto_pairing_spec.yml";
import {
    autoDetectPairs,
    autoPairWithCommonFilters,
    guessInitialFilterType,
    guessNameForPair,
    splitIntoPairedAndUnpaired,
} from "./pairing";

function mockDataset(name: string) {
    return { name };
}

const M1 = mockDataset("moo_1.fastq");
const M2 = mockDataset("moo_2.fastq");

const F1 = mockDataset("foo_1.fastq");
const F2 = mockDataset("foo_2.fastq");

const B1 = mockDataset("bar_1.fastq");
const B2 = mockDataset("bar_2.fastq");

const L1 = mockDataset("thisisalongmatchforpercentbasedtests_thisisthened.fastq");
const L2 = mockDataset("thisisalongmatchforpercentbasedtests_1thisisthened.fastq");

// These two matched on empty filters in playing around with the GUI and that confused me. -John
const E1 = mockDataset("cool11_fastq_2.fq");
const E2 = mockDataset("cool11_fastq_1.fq");

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

describe("guessNameForPair", () => {
    test("it should use the LCS and work with _1/_2 filters", () => {
        expect(guessNameForPair(mockDataset("moo_1.fastq"), mockDataset("moo_2.fastq"), "_1", "_2", true)).toEqual(
            "moo",
        );
    });

    test("it should use the LCS as a name and work with .1.fastq/.2.fastq filters", () => {
        expect(
            guessNameForPair(mockDataset("moo.1.fastq"), mockDataset("moo.2.fastq"), ".1.fastq", ".2.fastq", true),
        ).toEqual("moo");
    });

    test("it should use the LCS as a name and part of that is cutting out mismatched junk", () => {
        expect(
            guessNameForPair(
                mockDataset("moo_middledifferent_endssame.1.fastq"),
                mockDataset("moo_yuck_endssame.2.fastq"),
                ".1.fastq",
                ".2.fastq",
                true,
            ),
        ).toEqual("moo__endssame");
    });

    /* The way the filters and extension stripping are handled is less than ideal, this should work IMO for instance. -jmchilton
    test("it should use the LCS as a name and part of that is cutting out mismatched junk", () => {
        expect(guessNameForPair(mockDataset("moo.middledifferent.endssame.1.fastq"), mockDataset("moo.yuck.endssame.2.fastq"), ".1.fastq", ".2.fastq", true)).toEqual("moo.endssame");
    });
    */
});

describe("autoDetectPairs", () => {
    test("is should be able to match exact matches after filter...", () => {
        const paired = autoDetectPairs([M1], [M2], "_1", "_2", true);
        expect(paired).toHaveLength(1);
        const pair = paired[0];
        expect(pair?.name).toBe("moo");
    });

    test("is should be able to match exact matches after filter out of order...", () => {
        const paired = autoDetectPairs([B1, M1, F1], [F2, B2, M2], "_1", "_2", true);
        expect(paired).toHaveLength(3);
        const pairedNames = paired.map((p) => p.name);
        expect(pairedNames).toContain("bar");
        expect(pairedNames).toContain("moo");
        expect(pairedNames).toContain("bar");
    });
});

describe("autoPairWithCommonFilters", () => {
    test("it should return an indication of the filter type used", () => {
        const summary = autoPairWithCommonFilters([B1, M1, F1, F2, B2, M2], true);
        expect(summary.filterType).toEqual("illumina");
        expect(summary.pairs).toHaveLength(3);
        expect(summary.unpaired).toHaveLength(0);
    });

    test("it should return unpaired datasets if some are not matched off", () => {
        const summary = autoPairWithCommonFilters([B1, M1, F1, F2, B2], true);
        expect(summary.filterType).toEqual("illumina");
        expect(summary.pairs).toHaveLength(2);
        expect(summary.unpaired).toHaveLength(1);
        expect(summary.unpaired[0]?.name).toEqual("moo_1.fastq");
    });
});

describe("splitIntoPairedAndUnpaired", () => {
    test("if filters are empty, there should be not matching", () => {
        // we cannot deduce forward from reverse
        const summary = splitIntoPairedAndUnpaired([B1, M1, F1, F2, B2, L1, L2, E1, E2], "", "", true);
        expect(summary.pairs).toHaveLength(0);
    });
});

interface ExpectedPair {
    name: string;
    forward: string;
    reverse: string;
}

interface AutoPairingTest {
    doc?: string;
    inputs: string[];
    paired: Record<string, ExpectedPair>;
}

describe("fulfills auto pairing specification ", () => {
    test("the specification", () => {
        const tests = AUTO_PAIRING_SPECIFICATION;
        tests.forEach((test: AutoPairingTest) => {
            const inputs = test.inputs.map((name) => mockDataset(name));
            const summary = autoPairWithCommonFilters(inputs, true);
            for (const name in test.paired) {
                const expectedPair = test.paired[name] as ExpectedPair;
                const pair = summary.pairs?.find((p) => p.name === name);
                expect(pair).toBeDefined();
                expect(pair?.forward.name).toEqual(expectedPair.forward);
                expect(pair?.reverse.name).toEqual(expectedPair.reverse);
            }
        });
    });
});
