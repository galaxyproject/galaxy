// I'm using this as the reference for the requirement:
// https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/history/tutorial.html#advanced-searching

import { SearchParams } from "./SearchParams";
import { matchesSelector } from "pouchdb-selector-core";
import { STATES } from "components/History/model/states";
// import { show } from "jest/helpers";

// #region Test generators

const testPouchSelector = (userField, searchVal, goodDoc, badDoc) => {
    let pouchFieldName;
    let params;
    let selector;

    beforeEach(() => {
        params = new SearchParams();
        params.filterText = `${userField}="${searchVal}"`;
        selector = { $and: params.pouchFilters };
        pouchFieldName = params.getPouchFieldName(userField);
    });

    describe("pouchdb selector", () => {
        it("should have a row in the selector", () => {
            const hasRow = selector.$and.some((row) => row[pouchFieldName] !== undefined);
            expect(hasRow).toBeTruthy();
        });

        it("should return results with matching name field", () => {
            expect(matchesSelector(goodDoc, selector)).toBeTruthy();
        });

        it("should not return results where the name string appears in other fields", () => {
            expect(matchesSelector(badDoc, selector)).toBeFalsy();
        });
    });
};

const testUrlGeneration = (userField, searchVal) => {
    describe("request querystring", () => {
        it("should generate a query string with the expected server-side parameter", () => {
            const params = new SearchParams();
            params.filterText = `${userField}="${searchVal}"`;
            const serverField = params.getServerFieldName(userField);
            if (serverField) {
                const qs = params.historyContentQueryString;
                const queryParam = `${serverField}-contains=${encodeURIComponent(searchVal)}`;
                expect(qs.includes(queryParam)).toBeTruthy();
            }
        });
    });
};

// TODO: fix api to actually process the fields that it says it will
const testNotInUrl = (userField, searchVal) => {
    describe("request querystring", () => {
        it("should not send this filter, because it does not work on the api as described", () => {
            const params = new SearchParams();
            params.filterText = `${userField}="${searchVal}"`;
            const serverField = params.getServerFieldName(userField);
            const qs = params.historyContentQueryString;
            expect(qs.includes(serverField)).toBeFalsy();
        });
    });
};

//#endregion

describe("history contents search field text parsing", () => {
    describe("single field criteria", () => {
        // name="FASTQC on"
        // Any datasets with “FASTQC on” in the title, but avoids items which
        // have “FASTQC on” in other fields like the description or annotation.
        describe("name", () => {
            const searchField = "name";
            const searchTerm = "FASTQC on";

            const goodDoc = {
                _id: "anything",
                name: "asfasdfasdfasdf FASTQC onsdfasdfasdf",
                visible: true,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                otherField: "asfasdfasdfasdf FASTQC onsdfasdfasdf",
                visible: true,
                isDeleted: false,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);
            testUrlGeneration(searchField, searchTerm);
        });

        // format=vcf
        // Datasets with a specific format. Some formats are hierarchical, e.g.
        // searching for fastq will find fastq files but also fastqsanger and
        // fastqillumina files. You can see more formats in the upload dialogue
        describe("format", () => {
            const searchField = "format";
            const searchTerm = "vcf";

            const goodDoc = {
                _id: "anything",
                file_ext: "vcf",
                visible: true,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                file_ext: "notgonnamatch",
                visible: true,
                isDeleted: false,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);
            testUrlGeneration(searchField, searchTerm);
        });

        // database=hg19 Datasets with a specific reference genome
        describe("database", () => {
            const searchField = "database";
            const searchTerm = "hg19";

            const goodDoc = {
                _id: "anything",
                genome_build: "hg19",
                visible: true,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                genome_build: "somethingelse",
                visible: true,
                isDeleted: false,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);
            testUrlGeneration(searchField, searchTerm);
        });

        // annotation="first of five"
        describe("annotation", () => {
            const searchField = "annotation";
            const searchTerm = "first of fiv";

            const goodDoc = {
                _id: "anything",
                annotation: "this is the first of five",
                visible: true,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                annotation: "somethingelse",
                visible: true,
                isDeleted: false,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);
            testNotInUrl(searchField, searchTerm);
        });

        // NOTE: is annotation different from description?
        // description="This is data of a Borneo Orangutan" for dataset summary
        describe("description (same as annotation?)", () => {
            const searchField = "description";
            const searchTerm = "This is data of a Borneo Orangutan";

            const goodDoc = {
                _id: "anything",
                annotation: "asdfasdfThis is data of a Borneo Orangutansdfasdf",
                visible: true,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                annotation: "somethingelse",
                visible: true,
                isDeleted: false,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);
            testNotInUrl(searchField, searchTerm);
        });

        // info="started mapping"
        // for searching on job’s info field.
        // describe("job info", () => {});

        // tag=experiment1 tag=to_publish
        // for searching on (a partial) dataset tag.
        describe("tags", () => {
            const searchField = "tags";
            const searchTerm = "experiment1";

            const goodDoc = {
                _id: "anything",
                tags: ["experiment1", "experiment2"],
                visible: true,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                tags: ["nodice"],
                visible: true,
                isDeleted: false,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);
            testUrlGeneration(searchField, searchTerm);
        });

        // hid=25
        // A specific history item ID (based on the ordering in the history)
        describe("hid", () => {
            const searchField = "hid";
            const searchTerm = 25;

            const goodDoc = {
                _id: "anything",
                hid: 25,
                visible: true,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                hid: 200,
                visible: true,
                isDeleted: false,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);

            describe("request querystring", () => {
                it("hid should show up with an =, no text-search", () => {
                    const params = new SearchParams();
                    params.filterText = `${searchField}="${searchTerm}"`;
                    const qs = params.historyContentQueryString;
                    const serverField = params.getServerFieldName(searchField);
                    const fragment = `${serverField}=${searchTerm}`;
                    expect(qs.includes(fragment)).toBeTruthy();
                });
            });
        });

        // state=error
        // To show only datasets in a given state. Other options include ok,
        // running, paused, and new.
        describe("state", () => {
            const searchField = "state";
            const searchTerm = STATES.OK;

            const goodDoc = {
                _id: "anything",
                hid: 25,
                visible: true,
                state: STATES.OK,
                isDeleted: false,
            };

            const badDoc = {
                _id: "anything",
                hid: 200,
                visible: true,
                isDeleted: false,
                state: STATES.ERROR,
            };

            testPouchSelector(searchField, searchTerm, goodDoc, badDoc);

            describe("request querystring", () => {
                it("state should show up with an =, no text-search", () => {
                    const params = new SearchParams();
                    params.filterText = `${searchField}="${searchTerm}"`;
                    const qs = params.historyContentQueryString;
                    const serverField = params.getServerFieldName(searchField);
                    const fragment = `${serverField}=${searchTerm}`;
                    expect(qs.includes(fragment)).toBeTruthy();
                });
            });
        });
    });

    describe("multiple field criteria", () => {
        it("should allow a boolean AND combination of 2 filters", () => {
            const goodDoc = {
                _id: "anything",
                name: "sadfasdffooasdfasdf",
                tags: ["abc", "def", "blah"],
                visible: true,
                isDeleted: false,
            };

            const onlyOneMatch = {
                _id: "anything",
                name: "sadfasdffooasdfasdf",
                visible: true,
                isDeleted: false,
            };

            const theOtherMatch = {
                _id: "anything",
                tags: ["abc", "def", "blah"],
                visible: true,
                isDeleted: false,
            };

            const params = new SearchParams();
            params.filterText = "name=foo tag=blah";

            const selector = { $and: params.pouchFilters };

            expect(matchesSelector(goodDoc, selector)).toBeTruthy();
            expect(matchesSelector(onlyOneMatch, selector)).toBeFalsy();
            expect(matchesSelector(theOtherMatch, selector)).toBeFalsy();
        });
    });

    // TODO: There is a bug in the mongo query syntax implementation that stops us from having
    // two simultaneous criteria for the same field with the same type of operator, example
    // can't have { $and: [ { tag: { $regex: /abc/ }, { tag: { $regex: /def/ }}]}
    // https://github.com/pouchdb/pouchdb/issues/8265

    // I'll have to come up with a better solution for that AND intersection feature.

    xdescribe("deferring this functionality for now", () => {
        it("should allow a boolean AND combination of 2 of the same filter", () => {
            const doc = {
                _id: "anything",
                name: "abc def",
                visible: true,
                isDeleted: false,
            };

            // this should match
            const params = new SearchParams();
            params.filterText = "name=abc name=def";
            const selector = { $and: params.pouchFilters };
            expect(matchesSelector(doc, selector)).toBeTruthy();

            // this should not, it fails because of the bug which overwrites the regex on the field,
            // making it impossible to run 2 regexes against "name"
            const params2 = new SearchParams();
            params2.filterText = "name=sfsfssf name=def";
            const selector2 = params2.buildHistoryContentSelector();
            expect(matchesSelector(doc, selector2)).toBeFalsy();
        });

        it("should allow a boolean AND combination of 2 filters of for the same field, partial matches", () => {
            const doc = {
                _id: "anything",
                tags: ["abcasdfasdf", "def"],
                visible: true,
                isDeleted: false,
            };

            // this should match
            const params = new SearchParams();
            params.filterText = "tags=abc tag=def";
            const selector = { $and: params.pouchFilters };
            expect(matchesSelector(doc, selector)).toBeTruthy();

            // this should not
            const params2 = new SearchParams();
            params2.filterText = "tags=foo tag=def";
            const selector2 = { $and: params2.pouchFilters };
            expect(matchesSelector(doc, selector2)).toBeFalsy();
        });
    });
});
