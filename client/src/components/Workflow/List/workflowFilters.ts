import Filtering, { contains, equals, expandNameTag, toBool } from "@/utils/filtering";
export function helpHtml(activeList = "my") {
    let extra = "";
    if (activeList === "my") {
        extra = `<dt><code>is:published</code></dt>
        <dd>
            显示已发布的工作流。
        </dd>
        <dt><code>is:importable</code></dt>
        <dd>
            显示可导入的工作流（这也意味着它们是通过URL生成的）。
        </dd>
        <dt><code>is:shared_with_me</code></dt>
        <dd>
            显示其他用户直接与您共享的工作流。
        </dd>
        <dt><code>is:deleted</code></dt>
        <dd>显示已删除的工作流。</dd>`;
    } else if (activeList === "shared_with_me") {
        extra = `<dt><code>user:____</code></dt>
        <dd>
            显示由指定用户拥有的工作流。
        </dd>
        <dt><code>is:published</code></dt>
        <dd>
            显示已发布的工作流。
        </dd>`;
    } else {
        extra = `<dt><code>user:____</code></dt>
        <dd>
            显示由指定用户拥有的工作流。
        </dd>
        <dt><code>is:shared_with_me</code></dt>
        <dd>
            显示其他用户直接与您共享的工作流。
        </dd>`;
    }

    const conditionalHelpHtml = `<div>
        <p>此菜单可用于筛选显示的工作流。</p>

        <p>
            在此处输入的文本将用于搜索工作流名称和工作流标签。此外，高级筛选标签可用于更精确地细化搜索。
            筛选标签的格式为<code>&lt;标签名称&gt;:&lt;标签值&gt;</code>或
            <code>&lt;标签名称&gt;:'&lt;标签值&gt;'</code>。例如，要仅在工作流名称中搜索RNAseq，
            可以使用<code>name:rnsseq</code>。请注意，默认情况下搜索不区分大小写。如果使用带引号的标签版本，
            搜索将区分大小写，并且仅返回完全匹配项。因此<code>name:'RNAseq'</code>将只显示名称
            恰好为<code>RNAseq</code>的工作流。
        </p>

        <p>可用的筛选标签有：</p>
        <dl>
            <dt><code>name:____</code></dt>
            <dd>
                显示名称中包含给定字符序列的工作流。
            </dd>
            <dt><code>tag:____</code></dt>
            <dd>
                显示具有给定工作流标签的工作流。您也可以直接点击标签来基于该标签进行筛选。
            </dd>
            ${extra}
        </dl>
    </div>`;
    return conditionalHelpHtml;
}

export function getWorkflowFilters(activeList = "my") {
    const commonFilters = {
        name: { placeholder: "名称", type: String, handler: contains("name"), menuItem: true },
        n: { handler: contains("n"), menuItem: false },
        tag: {
            placeholder: "标签",
            type: "MultiTags",
            handler: contains("tag", "tag", expandNameTag),
            menuItem: true,
        },
        t: { type: "MultiTags", handler: contains("t", "t", expandNameTag), menuItem: false },
    } as const;

    if (activeList === "my") {
        return new Filtering(
            {
                ...commonFilters,
                published: {
                    placeholder: "已发布",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("published", "published", toBool),
                    menuItem: true,
                },
                importable: {
                    placeholder: "可导入",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("importable", "importable", toBool),
                    menuItem: true,
                },
                shared_with_me: {
                    placeholder: "与我共享",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("shared_with_me", "shared_with_me", toBool),
                    menuItem: true,
                },
                deleted: {
                    placeholder: "已删除",
                    type: Boolean,
                    boolType: "is",
                    handler: equals("deleted", "deleted", toBool),
                    menuItem: true,
                },
                bookmarked: {
                    placeholder: "已收藏",
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
                    placeholder: "所有者",
                    type: String,
                    handler: contains("user"),
                    menuItem: true,
                },
                u: { handler: contains("u"), menuItem: false },
                published: {
                    placeholder: "已发布",
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
                    placeholder: "所有者",
                    type: String,
                    handler: contains("user"),
                    menuItem: true,
                },
                u: { handler: contains("u"), menuItem: false },
                shared_with_me: {
                    placeholder: "与我共享",
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
