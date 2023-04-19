import { getAllValues } from "./utilities";

describe("drilldown component utilities", () => {
    it("get all values", () => {
        const options = [
            {
                value: "a",
                options: [
                    {
                        value: "aa",
                        options: [],
                    },
                    {
                        value: "ab",
                        options: [
                            {
                                value: "aba",
                                options: [
                                    {
                                        value: "abaa",
                                        options: [],
                                    },
                                ],
                            },
                            {
                                value: "abb",
                                options: [
                                    {
                                        value: "abba",
                                        options: [],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                value: "b",
                options: [
                    {
                        value: "ba",
                        options: [],
                    },
                    {
                        value: "bb",
                        options: [
                            {
                                value: "bba",
                                options: [
                                    {
                                        value: "bbaa",
                                        options: [],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ];
        expect(String(getAllValues(options))).toBe(
            String(["a", "b", "ba", "bb", "bba", "bbaa", "aa", "ab", "aba", "abb", "abba", "abaa"])
        );
    });
});
