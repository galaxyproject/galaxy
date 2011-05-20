<%inherit file="/base.mako"/>

<%def name="title()">Galaxy Administration</%def>

<h2>Administration</h2>

<p>The menu on the left provides the following features</p>
<ul>
    %if not trans.app.config.enable_next_gen_tool_shed:
        <li>
            <strong>Tools</strong>
            <p/>
            <ul>
                <li>
                    <strong>Tools awaiting approval</strong>
                </li>
                <p/>
                <li>
                    <strong>Browse by category</strong>
                </li>
                <p/>
                <li>
                    <strong>Browse all tools</strong>
                </li>
                <p/>
            </ul>
        </li>
    %endif
    <li>
        <strong>Categories</strong>
        <p/>
        <ul>
            <li>
                <strong>Manage categories</strong>
            </li>
            <p/>
        </ul>
    </li>
    <li>
        <strong>Security</strong>
        <p/>
        <ul>
            <li>
                <strong>Manage users</strong> - provides a view of the registered users and all groups and non-private roles associated 
                with each user.  
            </li>
            <p/>
            <li>
                <strong>Manage groups</strong> - provides a view of all groups along with the members of the group and the roles associated with
                each group (both private and non-private roles).  The group names include a link to a page that allows you to manage the users and 
                roles that are associated with the group.
            </li>
            <p/>
            <li>
                <strong>Manage roles</strong> - provides a view of all non-private roles along with the role type, and the users and groups that
                are associated with the role.  The role names include a link to a page that allows you to manage the users and groups that are associated 
                with the role.  The page also includes a view of the data library datasets that are associated with the role and the permissions applied 
                to each dataset.
            </li>
        </ul>
    </li>
    <p/>
</ul>
<br/>
