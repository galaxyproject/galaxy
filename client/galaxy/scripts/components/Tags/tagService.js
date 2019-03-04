/**
 * Generates a service object used by the tagging component to save, delete and
 * lookup potential tag options for the autocomplete feature. Standard typeahead
 * debouncing and ajax cancelling functionality is also provided here, though an
 * argument can be made that it more properly belongs in the component that is
 * handling the inputs.
 *
 * TODO: convert this python endpoint to a legit json REST service
 */

import axios from "axios";
import { createTag } from "./model";
import { Subject } from "rxjs";
import { filter, debounceTime, switchMap, distinctUntilChanged } from "rxjs/operators";

export function buildTagService({ id, itemClass, context, debounceInterval = 150 }) {
    /**
     * Save tag, input can be text string or tag model
     * @param {string|Tag} tag
     * @returns Promise yielding new tag model
     */
    async function saveTag(rawTag) {
        let tag = createTag(rawTag);
        let url = `/tag/add_tag_async?item_id=${id}&item_class=${itemClass}&context=${context}&new_tag=${tag.text}`;
        let response = await axios.get(url);
        if (response.status !== 200) {
            throw new Error(`Unable to save tag: ${tag}`);
        }
        return createTag(tag);
    }

    /**
     * Delete tag, input can be text string or tag model
     * @param {string|Tag} tag
     * @returns Promise yielding deleted tag model
     */
    async function deleteTag(rawTag) {
        let tag = createTag(rawTag);
        let url = `/tag/remove_tag_async?item_id=${id}&item_class=${itemClass}&context=${context}&tag_name=${tag.text}`;
        let response = await axios.get(url);
        if (response.status !== 200) {
            throw new Error(`Unable to delete tag: ${tag}`);
        }
        return tag;
    }

    /**
     * Looks up autocomplete options based on search text
     * @param {string} searchText
     * @returns Promise yielding an array of tag models
     */
    async function autocomplete(searchText) {
        let url = `/tag/tag_autocomplete_data?item_id=${id}&item_class=${itemClass}&q=${searchText}`;
        let response = await axios.get(url);
        if (response.status !== 200) {
            throw new Error(`Unable to retrieve autocomplete tags for search string: ${searchText}`);
        }
        return parseAutocompleteResults(response.data).map(createTag);
    }

    /**
     * Incoming autocomplete search text buffer
     */
    const _searchText = new Subject();

    return {
        // saves a single tag
        save: saveTag,

        // deletes a single tag
        delete: deleteTag,

        // returns options matching a search string for autocomplete this is
        // exposed for testing purposes only, in practice a consuming component
        // will set the autocompleteSearchText property and observe results by
        // subscribing to the autocompleteOptions observable property
        autocomplete,

        // input point for autocomplete text search
        set autocompleteSearchText(txt) {
            _searchText.next(txt);
        },

        // output of autocomplete search results
        // subscribe to this observable to get results
        autocompleteOptions: _searchText.pipe(
            filter(txt => txt.length),
            debounceTime(debounceInterval),
            distinctUntilChanged(),
            switchMap(autocomplete)
        )
    };
}

/**
 * Parser for the archaic result format in the current API.
 * See testData/autocompleteResponse.txt for a sample
 * @param {string} rawResponse
 */
export function parseAutocompleteResults(rawResponse) {
    return rawResponse
        .split("\n")
        .filter(line => line.includes("|"))
        .map(line => line.split("|")[0])
        .filter(label => label.length)
        .filter(label => label !== "#Header");
}
