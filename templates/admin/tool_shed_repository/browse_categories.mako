<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

%if message:
    ${render_msg( message, status )}
%endif
<div class="grid-header"><h2>Repositories by Category</h2><ul class="manage-table-actions"></ul>
    <div id="standard-search" style="display: block;">
        <table>
            <tbody><tr><td style="padding: 0;">
                <table>
                    <tbody>
                        <tr>
                            <td style="padding: 0;">
                                <form class="text-filter-form" column_key="free-text-search" action="/repository/browse_categories?sort=name" method="get">
                                    <span id="free-text-search-filtering-criteria"></span>
                                    <span class="search-box">
                                        <input class="search-box-input" id="input-free-text-search-filter" name="f-free-text-search" value="non-functional search box for cosmetic purposes" size="39" type="text">
                                        <button class="submit-image" type="submit" title="Search" />
                                    </span>
                                </form>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </td></tr>
            </tbody></table>
    </div>
    
    <div id="advanced-search" style="display: none; margin-top: 5px; border: 1px solid #ccc;">
        <table>
            <tbody><tr><td style="text-align: left" colspan="100">
                <a href="/repository/browse_categories?sort=name&amp;advanced-search=False" class="advanced-search-toggle">Close Advanced Search</a>
            </td></tr>
        </tbody></table>
    </div>
<div id="standard-search" style="display: block;"><table><tbody><tr><td style="padding: 0;"><table></table></td></tr><tr><td></td></tr></tbody></table></div><div id="advanced-search" style="display: none; margin-top: 5px; border: 1px solid #ccc;"><table><tbody><tr><td style="text-align: left" colspan="100"><a href="" class="advanced-search-toggle">Close Advanced Search</a></td></tr></tbody></table></div></div>
<table class="grid">
    <thead id="grid-table-header">
        <tr>
            <th id="Category.name-header"><a>Name</a><span class="sort-arrow"></span></th>
            <th id="Category.description-header"><a>Description</a><span class="sort-arrow"></span></th>
            <th id="null-header">Repositories<span class="sort-arrow"></span></th>
        </tr>
    </thead>
%for category in categories:
    <tr>
        <td>
            <a href="${h.url_for(controller='admin_toolshed', action='browse_tool_shed_category', category_id=category['id'], tool_shed_url=tool_shed_url)}">${category['name']}</a>
        </td>
        <td>${category['description']}</td>
        <td>${category['repositories']}</td>
    </tr>
%endfor
</table>
