<%inherit file="/base.mako"/>

<%def name="title()">Galaxy Administration</%def>

<h2>Administration</h2>

<p>Choose a task from the menu on the left.</p>
<p>
    <strong>Security</strong> - Data security in Galaxy is a new feature, so familiarize yourself with the details, which can be found 
    here or in our <a href="http://g2.trac.bx.psu.edu/wiki/SecurityFeatures" target="_blank">data security page</a>.  The data security 
    process incorporates users, groups and roles, and enables the application of certain restrictions on datasets.  The default process
    is to not apply any security restrictions to datasets, and data becomes more restricted with each new "permission restriction" applied
    to it.  With no restrictions, users should not see any difference in the way Galaxy has always worked.  The general definitions of 
    these entities are:
    <ul>
        <li>
            <strong>Users</strong> - registered Galaxy users that have created a Galaxy account.  Users can be members of a group and can
            be associated with 1 or more roles.  If a user is not authenticated during a Galaxy session, they will not have access to any 
            of the security features, and datasets they create during that session will have no security restrictions applied to them
            (i.e., they will be considered "public").
        </li>
        <p></p>
        <li>
            <strong>Groups</strong> - a set of 0 or more users which are considered members of the group.  Groups can be associated with 0
            or more roles, simplifying the process of applying "permission restrictions" to the data between a select group of users.
        </li>
        <p></p>
        <li>
            <strong>Roles</strong> - associate users and groups with specific permissions on datasets.  For example, users in groups A and B 
            can be associated with role C which gives them the "access" permission on datasets D, E and F.  Roles have a type which is currently
            one of the following:
            <ul>
                <li>
                    <strong>private</strong> - every user is associated automatically with their own private role, and administrators cannot 
                    manage them.
                </li>
                <li>
                    <strong>user</strong> - this is currently not used, but eventually any registered user will be able to create a new role
                    and this will be it's type.
                </li>
                <li>
                    <strong>sharing</strong> - a role created automatically during a Galaxy session that enables a user to share data with 
                    another user.  This can generally be considered a temporary role, but this role type is evolving.
                </li>
                <li><strong>admin</strong> - a role created by a Galaxy administrator.</li>
            </ul>
        </li>
        <p></p>
        <li>
            <strong>Permissions</strong> - for any dataset, applying one of the following role "permission restrictions" will restrict the
            use of the dataset.
            <ul>
                <li>
                    <strong>access</strong> - users associated with the role can import this dataset into their history for analysis.
                    <p>
                        If no roles with the 'access' permission restriction are associated with a dataset, the dataset is "public" and may 
                        be shared with anyone.  Public library datasets will be accessible to all users (as well as anyone not logged in 
                        during a Galaxy session) from the list of libraries displayed when the "Access Libraries stored locally" tool is used.
                    </p>
                    <p>
                        Associating a dataset with a role that includes the "access" permission restriction narrows the set of users that can
                        access it.  For example, if 'Role A' includes the "access" permission restriction and 'Role A' is associated with the dataset,
                        only those users and groups who are associated with 'Role A' may access the dataset.
                    </p>
                    <p>
                        If multiple roles that include the "access" permission restriction are associated with a dataset, access to the
                        dataset is derived from the intersection of the users associated with the roles.  For example, if 'Role A' and 'Role B' are 
                        associated with a dataset, only those users and groups who are associated with both 'Role A' AND 'Role B' may access the dataset.
                    </p>
                    <p>
                        In order for a user to make a dataset private to just themselves, they should associate the dataset with their private role
                        (the role identical to their Galaxy user name / email address).  Associating additional roles that include the 'access' 
                        permission restriction is not advised since the behavior will probably not be as expected.  Role permission restrictions
                        are always logically "ANDed" together, so only the user will be able to access the dataset since they are the only member of 
                        their "private role".  To make a dataset private to themselves and one or more other users, the user should create a new role 
                        (note: this functionality is still under development for non administrator users) and associate the dataset with that role, 
                        not their "private role".
                    </p>
                    <p>
                        Private data (data associated with roles that include the "access" permission restriction) must be made public in order 
                        to be used with external sources, such as the "view at UCSC" link, or the "Perform genome analysis and prediction with EpiGRAPH" 
                        tool.  Being "made public" means removing the association of all roles that include the "access" permission restriction from
                        the dataset.
                    <p>
                </li>
                <li><strong>edit metadata</strong> - users associated with the role can edit this dataset's metadata in the dataset library.</li>
                <li>
                    <strong>manage permissions</strong> - users associated with the role can manage the roles associated with this dataset.  If no 
                    roles that include the 'manage permissions' are associated with the dataset, only administrators can modify it's permission
                    restrictions.
                </li>
            </ul>
        </li>
    </ul>
</p>
<p>The menu on the left provides the following features</p>
<ul>
    <li>
        <strong>Manage users</strong> - provides a view of the registered users and all groups and non-private roles associated 
        with each user.  
    </li>
    <p></p>
    <li>
        <strong>Manage groups</strong> - provides a view of all groups along with the members of the group and the roles associated with
        each group (both private and non-private roles).  Non-private roles include a link to a page that allows you to manage the users
        and groups that are associated with the role.  The page also includes a view of the library datasets that are associated with the
        role and the various "permission restrictions" applied to each dataset.
    </li>
    <p></p>
    <li>
        <strong>Manage non-private roles</strong> - provides a view of all non-private roles along with the role type, and the users and groups that
        are associated with the role.
    </li>
    <p></p>
    <li>
        <strong>Manage libraries</strong> - Dataset libraries enable a Galaxy administrator to upload datasets into a library.  Only 
        administrators can create dataset libraries and maintain their contents ( datasets ) and the security applied to them.  From 
        the Galaxy analysis view, the "Access Libraries stored locally" tool in the "Get Data" tool 
        section allows users to access the datasets in a library ( if the user is not restricted from accessing the datasets by the 
        security rules applied to them ) by "uploading" them into their histories.  This "uploading" process will not make a copy of 
        the dataset, however, but will be a sort of pointer to the dataset on disk.  This approach allows for multiple users to have 
        access to a single ( possibly very large ) dataset on disk.
    </li>
</ul>
<p></p><p></p>
