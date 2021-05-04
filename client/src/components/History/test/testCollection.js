// Doctored collection & children for unit tests
import rawCollection from "./json/DatasetCollection";
import rawNestedCollection from "./json/DatasetCollection.nested.json";
import rawCollectionContent from "./json/collectionContent.json";
import rawNestedCollectionContent from "./json/collectionContent.nested.json";

// Sample collection for CCP tests

const parent_url = "/foo";

export const testCollectionContent = rawCollectionContent.map((props) => ({ ...props, parent_url }));

export const testCollection = Object.assign({}, rawCollection, {
    contents_url: parent_url,
    element_count: testCollectionContent.length,
});

export const testNestedCollection = Object.assign({}, rawNestedCollection, {
    parent_url: parent_url,
    contents_url: "/foo/bar",
    element_count: rawNestedCollectionContent.length,
});

// a list of element_indexes handy for testing
export const indices = (list) => list.map(({ element_index, _id, parent_url }) => ({ element_index, _id, parent_url }));
