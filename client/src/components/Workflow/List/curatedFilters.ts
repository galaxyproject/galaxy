import Filtering, { contains, expandNameTag } from "@/utils/filtering";

/**
 * Deliberately decoupled from `workflowFilters.ts`: the curated endpoint only
 * honours name and tag, and `hasInvalidFilters` correctly rejects anything else.
 */
export function curatedWorkflowFilters() {
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
    } as const;

    return new Filtering({ ...curatedFilters }, undefined, false);
}

export function curatedHelpHtml() {
    return `<div>
        <p>This menu can be used to filter the curated workflows displayed.</p>

        <p>
            Text entered here will be searched against workflow names, descriptions and
            tags. Additionally, advanced filtering tags can be used to refine the search
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
            </dd>
        </dl>
    </div>`;
}
