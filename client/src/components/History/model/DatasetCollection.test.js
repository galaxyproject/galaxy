import { Content } from "./Content";
import { DatasetCollection } from "./DatasetCollection";
import { STATES } from "./states";

// test data
import raw from "components/providers/History/test/json/DatasetCollection.json";

// error on load
import rawError from "components/providers/History/test/json/DatasetCollection.error.json";

// mixed bag
import rawProcessing from "components/providers/History/test/json/DatasetCollection.processing.json";

describe("DatasetCollection", () => {
    const model = new DatasetCollection(raw);
    const errorModel = new DatasetCollection(rawError);
    const processingModel = new DatasetCollection(rawProcessing);

    test("it should be the right type", () => {
        expect(model).toBeInstanceOf(DatasetCollection);
        expect(model).toBeInstanceOf(Content);
        expect(errorModel).toBeInstanceOf(DatasetCollection);
        expect(errorModel).toBeInstanceOf(Content);
        expect(processingModel).toBeInstanceOf(DatasetCollection);
        expect(processingModel).toBeInstanceOf(Content);
    });

    describe("jobStateSummary", () => {
        test("should report a job count", () => {
            expect(model.jobSummary.jobCount).toEqual(0);
            expect(processingModel.jobSummary.jobCount).toEqual(6);
        });

        test("errored collection", () => {
            expect(errorModel.jobSummary.errorCount).toBeGreaterThan(0);
            expect(errorModel.jobSummary.jobCount).toBeGreaterThan(0);
            expect(errorModel.jobSummary.state).toEqual(STATES.ERROR);
        });
    });
});
