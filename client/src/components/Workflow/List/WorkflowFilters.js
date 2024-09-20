import Filtering, { contains, equals, expandNameTag, toBool } from "utils/filtering";

export function helpHtml(activeList = "my") {
    let extra = "";
    if (activeList === "my") {
        extra = `<dt><code>is:published</code></dt>
        <dd>
            Shows published workflows.
        </dd>
        <dt><code>is:importable</code></dt>
        <dd>
            Shows importable workflows (this also means they are URL generated).
        </dd>
        <dt><code>is:shared_with_me</code></dt>
        <dd>
            Shows workflows shared by another user directly with you.
        </dd>
        <dt><code>is:deleted</code></dt>
        <dd>Shows deleted workflows.</dd>`;
    } else if (activeList === "shared_with_me") {
        extra = `<dt><code>user:____</code></dt>
        <dd>
            Shows workflows owned by the given user.
        </dd>
        <dt><code>is:published</code></dt>
        <dd>
            Shows published workflows.
        </dd>`;
    } else {
        extra = `<dt><code>user:____</code></dt>
        <dd>
            Shows workflows owned by the given user.
        </dd>
        <dt><code>is:shared_with_me</code></dt>
        <dd>
            Shows workflows shared by another user directly with you.
        </dd>`;
    }

    const conditionalHelpHtml = `<div>
        <p>This menu can be used to filter the workflows displayed.</p>

        <p>
            Text entered here will be searched against workflow names and workflow
            tags. Additionally, advanced filtering tags can be used to refine the
            search more precisely. Filtering tags are of the form
            <code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or
            <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>. For instance to
            search just for RNAseq in the workflow name,
            <code>name:rnsseq</code> can be used. Notice by default the search is
            not case-sensitive. If the quoted version of tag is used, the search is
            case sensitive and only full matches will be returned. So
            <code>name:'RNAseq'</code> would show only workflows named exactly
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
            ${extra}
        </dl>
    </div>`;
    return conditionalHelpHtml;
}

export function WorkflowFilters(activeList = "my") {
    const commonFilters = {
        name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
        n: { handler: contains("n"), menuItem: false },
        tag: {
            placeholder: "tag(s)",
            type: "MultiTags",
            handler: contains("tag", "tag", expandNameTag),
            menuItem: true,
        },
        t: { type: "MultiTags", handler: contains("t", "t", expandNameTag), menuItem: false },
    };

    if (activeList === "my") {
        return new Filtering(
            {
                ...commonFilters,
                published: {
                    placeholder: "Published",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("published", "published", toBool),
                    menuItem: true,
                },
                importable: {
                    placeholder: "Importable",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("importable", "importable", toBool),
                    menuItem: true,
                },
                shared_with_me: {
                    placeholder: "Shared with me",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("shared_with_me", "shared_with_me", toBool),
                    menuItem: true,
                },
                deleted: {
                    placeholder: "Deleted",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("deleted", "deleted", toBool),
                    menuItem: true,
                },
                bookmarked: {
                    placeholder: "Bookmarked",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("bookmarked", "bookmarked", toBool),
                    menuItem: true,
                },
            },
            undefined,
            false,
            false
        );
    } else if (activeList === "shared_with_me") {
        return new Filtering(
            {
                ...commonFilters,
                user: {
                    placeholder: "owner",
                    type: String,
                    handler: contains("user"),
                    menuItem: true,
                },
                u: { handler: contains("u"), menuItem: false },
                published: {
                    placeholder: "Published",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("published", "published", toBool),
                    menuItem: true,
                },
            },
            undefined,
            false,
            false
        );
    } else {
        return new Filtering(
            {
                ...commonFilters,
                user: {
                    placeholder: "owner",
                    type: String,
                    handler: contains("user"),
                    menuItem: true,
                },
                u: { handler: contains("u"), menuItem: false },
                shared_with_me: {
                    placeholder: "Shared with me",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("shared_with_me", "shared_with_me", toBool),
                    menuItem: true,
                },
            },
            undefined,
            false,
            false
        );
    }
}
