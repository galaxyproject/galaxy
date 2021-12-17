import { Content } from "./Content";
import { DatasetCollection } from "./DatasetCollection";
import { STATES } from "./states";

// test data
import raw from "components/providers/History/test/json/DatasetCollection.json";

// error on load
import rawError from "components/providers/History/test/json/DatasetCollection.error.json";

// mixed bag
import rawProcessing from "components/providers/History/test/json/DatasetCollection.processing.json";
import rawHomogeneous from "components/providers/History/test/json/DatasetCollection.homogeneous.json";
import rawHeterogeneous from "components/providers/History/test/json/DatasetCollection.heterogeneous.json";

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

    describe("Homogeneous collection", () => {
        const homogeneous = new DatasetCollection(rawHomogeneous);
        it("should have a homogeneous datatype", () => {
            expect(homogeneous.isHomogeneous).toBe(true);
            expect(homogeneous.homogeneousDatatype).toBe("txt");
        });
    });

    describe("Heterogeneous collection", () => {
        const heterogeneous = new DatasetCollection(rawHeterogeneous);
        it("should not have a homogeneous datatype", () => {
            expect(heterogeneous.isHomogeneous).toBe(false);
            expect(heterogeneous.homogeneousDatatype).toBe("");
        });
    });
});
