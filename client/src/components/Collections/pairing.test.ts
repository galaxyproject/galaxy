import { describe, expect, test } from "vitest";

import AUTO_PAIRING_SPECIFICATION from "./auto_pairing_spec.yml";
import {
    autoDetectPairs,
    autoPairWithCommonFilters,
    guessInitialFilterType,
    guessNameForPair,
    isValidFilter,
    splitIntoPairedAndUnpaired,
} from "./pairing";

function namedDataset(name: string) {
    return { name };
}

const mooForward = namedDataset("moo_1.fastq");
const mooReverse = namedDataset("moo_2.fastq");

const fooForward = namedDataset("foo_1.fastq");
const fooReverse = namedDataset("foo_2.fastq");

const barForward = namedDataset("bar_1.fastq");
const barReverse = namedDataset("bar_2.fastq");

const longNameFirst = namedDataset("thisisalongmatchforpercentbasedtests_thisisthened.fastq");
const longNameSecond = namedDataset("thisisalongmatchforpercentbasedtests_1thisisthened.fastq");

// These two matched on empty filters in playing around with the GUI and that confused me. -John
const emptyFilterFirst = namedDataset("cool11_fastq_2.fq");
const emptyFilterSecond = namedDataset("cool11_fastq_1.fq");

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
        expect(guessNameForPair(namedDataset("moo_1.fastq"), namedDataset("moo_2.fastq"), "_1", "_2", true)).toEqual(
            "moo",
        );
    });

    test("it should use the LCS as a name and work with .1.fastq/.2.fastq filters", () => {
        expect(
            guessNameForPair(namedDataset("moo.1.fastq"), namedDataset("moo.2.fastq"), ".1.fastq", ".2.fastq", true),
        ).toEqual("moo");
    });

    test("it should use the LCS as a name and part of that is cutting out mismatched junk", () => {
        expect(
            guessNameForPair(
                namedDataset("moo_middledifferent_endssame.1.fastq"),
                namedDataset("moo_yuck_endssame.2.fastq"),
                ".1.fastq",
                ".2.fastq",
                true,
            ),
        ).toEqual("moo__endssame");
    });

    /* The way the filters and extension stripping are handled is less than ideal, this should work IMO for instance. -jmchilton
    test("it should use the LCS as a name and part of that is cutting out mismatched junk", () => {
        expect(guessNameForPair(namedDataset("moo.middledifferent.endssame.1.fastq"), namedDataset("moo.yuck.endssame.2.fastq"), ".1.fastq", ".2.fastq", true)).toEqual("moo.endssame");
    });
    */
});

describe("autoDetectPairs", () => {
    test("matches names after removing forward and reverse filters", () => {
        const paired = autoDetectPairs([mooForward], [mooReverse], "_1", "_2", true);
        expect(paired).toHaveLength(1);
        const pair = paired[0];
        expect(pair?.name).toBe("moo");
    });

    test("matches datasets when forward and reverse inputs have different orders", () => {
        const paired = autoDetectPairs(
            [barForward, mooForward, fooForward],
            [fooReverse, barReverse, mooReverse],
            "_1",
            "_2",
            true,
        );
        expect(paired).toHaveLength(3);
        const pairedNames = paired.map((p) => p.name);
        expect(pairedNames).toContain("bar");
        expect(pairedNames).toContain("moo");
        expect(pairedNames).toContain("bar");
        expect(pairedNames).toContain("foo");
    });
});

describe("autoPairWithCommonFilters", () => {
    test("it should return an indication of the filter type used", () => {
        const summary = autoPairWithCommonFilters(
            [barForward, mooForward, fooForward, fooReverse, barReverse, mooReverse],
            true,
        );
        expect(summary.filterType).toEqual("illumina");
        expect(summary.pairs).toHaveLength(3);
        expect(summary.unpaired).toHaveLength(0);
    });

    test("it should return unpaired datasets if some are not matched off", () => {
        const summary = autoPairWithCommonFilters([barForward, mooForward, fooForward, fooReverse, barReverse], true);
        expect(summary.filterType).toEqual("illumina");
        expect(summary.pairs).toHaveLength(2);
        expect(summary.unpaired).toHaveLength(1);
        expect(summary.unpaired[0]?.name).toEqual("moo_1.fastq");
    });
});

describe("splitIntoPairedAndUnpaired", () => {
    test("leaves datasets unpaired when both filters are empty", () => {
        // we cannot deduce forward from reverse
        const summary = splitIntoPairedAndUnpaired(
            [
                barForward,
                mooForward,
                fooForward,
                fooReverse,
                barReverse,
                longNameFirst,
                longNameSecond,
                emptyFilterFirst,
                emptyFilterSecond,
            ],
            "",
            "",
            true,
        );
        expect(summary.pairs).toHaveLength(0);
    });

    test("a filter that is not a valid regular expression matches nothing", () => {
        const elements = [barForward, mooForward, fooForward, fooReverse, barReverse];
        const summary = splitIntoPairedAndUnpaired(elements, "_1 (R1", "_2", true);
        expect(summary.pairs).toHaveLength(0);
        expect(summary.unpaired).toEqual(elements);
    });
});

describe("isValidFilter", () => {
    test("accepts regular expressions and rejects unterminated groups", () => {
        expect(isValidFilter("_1")).toBe(true);
        expect(isValidFilter("_1 (R1 paired)")).toBe(true);
        expect(isValidFilter("_1 (R1")).toBe(false);
    });
});

interface ExpectedPair {
    forward: string;
    reverse: string;
}

interface AutoPairingTest {
    doc: string;
    inputs: string[];
    paired: Record<string, ExpectedPair>;
}

// The YAML import is untyped; keep its fixture shape explicit at the file boundary.
const pairingExamples: AutoPairingTest[] = AUTO_PAIRING_SPECIFICATION;

describe("auto pairing specification", () => {
    test.each(pairingExamples)("$doc", ({ inputs, paired }) => {
        const summary = autoPairWithCommonFilters(inputs.map(namedDataset), true);
        for (const [name, expectedPair] of Object.entries(paired)) {
            const pair = summary.pairs?.find((p) => p.name === name);
            expect(pair).toBeDefined();
            expect(pair?.forward.name).toEqual(expectedPair.forward);
            expect(pair?.reverse.name).toEqual(expectedPair.reverse);
        }
    });
});
