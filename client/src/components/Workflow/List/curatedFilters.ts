import Filtering, { contains, equals, expandNameTag, toBool } from "@/utils/filtering";

/**
 * Deliberately decoupled from `workflowFilters.ts`: the curated endpoint only
 * honours name, tag, collection and `is:runnable`, and `hasInvalidFilters`
 * correctly rejects anything else.
 *
 * `collection:` and `is:runnable` stay valid in local mode, where they match
 * nothing, but are only offered in the menu for the IWC catalog.
 */
export function curatedWorkflowFilters(isIwcCatalog: boolean) {
    const curatedFilters = {
        name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
        n: { handler: contains("n"), menuItem: false },
        tag: {
            placeholder: "tag(s)",
            type: "MultiTags",
            handler: contains("tag", "tag", expandNameTag),
            menuItem: true,
        },
        t: { type: "MultiTags", handler: contains("t", "t", expandNameTag), menuItem: false },
        collection: {
            placeholder: "collection",
            type: String,
            handler: contains("collection"),
            menuItem: isIwcCatalog,
        },
        c: { handler: contains("c"), menuItem: false },
        runnable: {
            placeholder: "Ready to run here",
            type: Boolean,
            boolType: "is",
            handler: equals("runnable", "runnable", toBool),
            menuItem: isIwcCatalog,
        },
    } as const;

    return new Filtering({ ...curatedFilters }, undefined, false);
}

/** Collections and the tool check are IWC catalog features, so local mode never advertises them. */
export function curatedHelpHtml(isIwcCatalog: boolean) {
    const searchedFields = isIwcCatalog ? "names, descriptions, tags and collections" : "names, descriptions and tags";
    const catalogFilters = isIwcCatalog
        ? `
            <dt><code>collection:____</code></dt>
            <dd>
                Shows workflows in the given IWC collection. The collection buttons above
                the search, or a collection badge on a card, set this for you.
            </dd>
            <dt><code>is:runnable</code></dt>
            <dd>
                Shows only workflows whose tools are all installed on this Galaxy. The
                "Ready to run here" button above the search sets this for you.
            </dd>`
        : "";
    return `<div>
        <p>This menu can be used to filter the curated workflows displayed.</p>

        <p>
            Text entered here will be searched against workflow ${searchedFields}. Additionally, advanced filtering tags can be used to refine the search
            more precisely. Filtering tags are of the form
            <code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or
            <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>. For instance to search
            just for RNAseq in the workflow name, <code>name:rnaseq</code> can be used.
            Notice by default the search is not case-sensitive. If the quoted version of
            a tag is used, only full matches will be returned. So
            <code>tag:'RNAseq'</code> would show only workflows tagged exactly
            <code>RNAseq</code>.
        </p>

        <p>The available filtering tags are:</p>
        <dl>
            <dt><code>name:____</code></dt>
            <dd>
                Shows workflows with the given sequence of characters in their names.
            </dd>
            <dt><code>tag:____</code></dt>
            <dd>
                Shows workflows with the given workflow tag. You may also click
                on a tag to filter on that tag directly.
            </dd>${catalogFilters}
        </dl>
    </div>`;
}
