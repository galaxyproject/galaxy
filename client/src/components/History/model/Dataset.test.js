import { Content } from "./Content";
import { Dataset } from "./Dataset";

import raw from "components/providers/History/test/json/Dataset.json";

const elementIdentifier = "collection_element1";

describe("Dataset", () => {
    const historyDataset = new Dataset(raw);
    const collectionElement = new Dataset({ ...raw, element_identifier: elementIdentifier });

    test("it should be the right type", () => {
        expect(historyDataset).toBeInstanceOf(Dataset);
        expect(historyDataset).toBeInstanceOf(Content);

        expect(collectionElement).toBeInstanceOf(Dataset);
        expect(collectionElement).toBeInstanceOf(Content);
    });
    test("dataset title should include name", () => {
        expect(historyDataset.name).toBe("M117C1-ch_2.fq.fastqsanger");
        expect(historyDataset.title).toBe("M117C1-ch_2.fq.fastqsanger");
    });
    test("collection element title should include element identifier for collection element", () => {
        expect(collectionElement.title).toBe(elementIdentifier);
    });
    test("dataset name can be edited", () => {
        expect(historyDataset.canEditName).toBeTruthy();
    });
    test("collection element name cannot be edited", () => {
        expect(collectionElement.canEditName).toBeFalsy();
    });
});
