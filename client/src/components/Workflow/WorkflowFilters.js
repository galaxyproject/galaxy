import Filtering, { contains, equals, expandNameTag, toBool } from "utils/filtering";

export const helpHtml = `<div>
<p>This input can be used to filter the workflows displayed.</p>

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
    <dt><code>name</code></dt>
    <dd>
        Shows workflows with the given sequence of characters in their names.
    </dd>
    <dt><code>tag</code></dt>
    <dd>
        Shows workflows with the given workflow tag. You may also click
        on a tag to filter on that tag directly.
    </dd>
    <dt><code>is:published</code></dt>
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
    <dd>Shows deleted workflows.</dd>
</dl>
</div>`;

const validFilters = {
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    user: {
        placeholder: "owner",
        type: String,
        handler: contains("user"),
        menuItem: false,
    },
    tag: {
        placeholder: "tag(s)",
        type: "MultiTags",
        handler: contains("tag", "tag", expandNameTag),
        menuItem: true,
    },
    published: {
        placeholder: "Filter on published workflows",
        type: Boolean,
        boolType: "is",
        handler: equals("published", "published", toBool),
        menuItem: true,
    },
    importable: {
        placeholder: "Filter on importable workflows",
        type: Boolean,
        boolType: "is",
        handler: equals("importable", "importable", toBool),
        menuItem: true,
    },
    shared_with_me: {
        placeholder: "Filter on workflows shared with me",
        type: Boolean,
        boolType: "is",
        handler: equals("shared_with_me", "shared_with_me", toBool),
        menuItem: true,
    },
    deleted: {
        placeholder: "Filter on deleted workflows",
        type: Boolean,
        boolType: "is",
        handler: equals("deleted", "deleted", toBool),
        menuItem: true,
    },
};

export const WorkflowFilters = new Filtering(validFilters, undefined, false, false);

const validPublishedFilters = {
    ...validFilters,
    user: {
        ...validFilters.user,
        menuItem: true,
    },
    published: {
        ...validFilters.published,
        default: true,
        menuItem: false,
    },
    shared_with_me: {
        ...validFilters.shared_with_me,
        menuItem: false,
    },
    importable: {
        ...validFilters.importable,
        menuItem: false,
    },
};

export const PublishedWorkflowFilters = new Filtering(validPublishedFilters, undefined, false, false);
