<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Galaxy Administration</%def>

<h2>Administration</h2>

%if message:
    ${render_msg( message, status )}
%else:
    <p>The menu on the left provides the following features</p>
    <ul>
        <li><strong>Security</strong> - see the <strong>Data Security and Data Libraries</strong> section below for details
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
        <li><strong>Data</strong>
            <p/>
            <ul>
                <li>
                    <strong>Manage data libraries</strong> - Data libraries enable a Galaxy administrator to upload datasets into a data library.  Currently,
                    only administrators can create data libraries.
                    <p/>
                    When a data library is first created, it is considered "public" since it will be displayed in the "Data Libraries" view for any user, even 
                    those that are not logged in.  The Galaxy administrator can restrict access to a data library by associating roles with the data library's 
                    "access library" permission.  This permission will conservatively override the [dataset] "access" permission for the data library's contained 
                    datasets.
                    <p/>
                    For example, if a data library's "access library" permission is associated with Role1 and the data library contains "public" datasets, the 
                    data library will still only be displayed to those users that have Role1.  However, if the data library's "access library" permission is 
                    associated with both Role1 and Role2 and the data library contains datasets whose [dataset] "access" permission is associated with only Role1, 
                    then users that have Role2 will be able to access the library, but will not see those contained datasets whose [dataset] "access" permission 
                    is associated with only Role1.
                    <p/>
                    In addition to the "access library" permission, permission to perform the following functions on the data library (and its contents) can 
                    be granted to users (a library item is one of: a data library, a library folder, a library dataset).
                    <p/>
                    <ul>
                        <li><strong>add library item</strong> - Users that have the role can add library items to this data library or folder</li>
                        <li><strong>modify library item</strong> - Users that have the role can modify this library item</li>
                        <li><strong>manage library permissions</strong> - Users that have the role can manage permissions applied to this library item</li>
                    </ul>
                    <p/>
                    The default behavior is for no permissions to be applied to a data library item, but applied permissions are inherited downward (with the exception
                    of the "access library" permission, which is only available on the data library itself).  Because of this, it is important to set desired permissions 
                    on a new data library when it is created.  When this is done, new folders and datasets added to the data library will automatically inherit those 
                    permissions.  In the same way, permissions can be applied to a folder, which will be automatically inherited by all contained datasets and sub-folders.
                    <p/>
                    The "Data Libraries" menu item allows users to access the datasets in a data library as long as they are not restricted from accessing them.
                    Importing a library dataset into a history will not make a copy of the dataset, but will be a "pointer" to the dataset on disk.  This
                    approach allows for multiple users to use a single (possibly very large) dataset file.
                </li>
            </ul>
        </li>
        <p/>
        <li><strong>Server</strong>
            <p/>
            <ul>
                <li>
                    <strong>Reload a tool's configuration</strong> - allows a new version of a tool to be loaded while the server is running
                </li>
                <p/>
                <li>
                    <strong>Profile memory usage</strong> - measures system memory used for certain Galaxy functions
                </li>
                <p/>
                <li>
                    <strong>Manage jobs</strong> - displays all jobs that are currently not finished (i.e., their state is new, waiting, queued, or
                    running).  Administrators are able to cleanly stop long-running jobs. 
                </li>
            </ul>
        </li>
        <p/>
        <li><strong>Forms</strong>
            <p/>To be completed
        </li>
        <p/>
        <li><strong>Sequencing Requests</strong>
            <p/>To be completed
        </li>
        <p/>
        <li><strong>Cloud</strong>
            <p/>To be completed
        </li>
    </ul>
    <p/>
    <p><strong>Data Security and Data Libraries</strong></p>
    <p/>
    <strong>Security</strong> - Data security in Galaxy is a new feature, so familiarize yourself with the details which can be found 
    here or in our <a href="http://wiki.galaxyproject.org/Learn/Security%20Features" target="_blank">data security page</a>.  The data security 
    process incorporates users, groups and roles, and enables the application of certain permissions on datasets, specifically "access"
    and "manage permissions".  By default, the "manage permissions" permission is associated with the dataset owner's private role, and
    the "access" permission is not set, making the dataset public.  With these default permissions, users should not see any difference
    in the way Galaxy has behaved in the past.
    <ul>
        <li>
            <strong>Users</strong> - registered Galaxy users that have created a Galaxy account.  Users can belong to groups and can
            be associated with 1 or more roles.  If a user is not authenticated during a Galaxy session, they will not have access to any 
            of the security features, and datasets they create during that session will have no permissions applied to them (i.e., they
            will be considered "public", and no one will be allowed to change permissions on them).
        </li>
        <p/>
        <li>
            <strong>Groups</strong> - a set of 0 or more users which are considered members of the group.  Groups can be associated with 0
            or more roles, simplifying the process of applying permissions to the data between a select group of users.
        </li>
        <p/>
        <li>
            <strong>Roles</strong> - associate users and groups with specific permissions on datasets.  For example, users in groups A and B 
            can be associated with role C which gives them the "access" permission on datasets D, E and F.  Roles have a type which is currently
            one of the following:
            <ul>
                <li>
                    <strong>private</strong> - every user is associated automatically with their own private role.  Administrators cannot 
                    manage private roles.
                </li>
                <li>
                    <strong>user</strong> - this is currently not used, but eventually any registered user will be able to create a new role
                    and this will be its type.
                </li>
                <li>
                    <strong>sharing</strong> - a role created automatically during a Galaxy session that enables a user to share data with 
                    another user.  This can generally be considered a temporary role.
                </li>
                <li><strong>admin</strong> - a role created by a Galaxy administrator.</li>
            </ul>
        </li>
        <p/>
        <li>
            <strong>Dataset Permissions</strong> - applying the following permissions will to a dataset will result in the behavior described.
            <ul>
                <li>
                    <strong>access</strong> - users associated with the role can import this dataset into their history for analysis.
                    <p>
                        If no roles with the "access" permission are associated with a dataset, the dataset is "public" and may be accessed by anyone 
                        that can access the data library in which it is contained.  See the <strong>Manage data libraries</strong> section above for 
                        details.  Public datasets contained in public data libraries will be accessible to all users (as well as anyone not logged in 
                        during a Galaxy session) from the list of data libraries displayed when the "Data Libraries" menu item is selected.
                    </p>
                    <p>
                        Associating a dataset with a role that includes the "access" permission restricts the set of users that can access it.  
                        For example, if 'Role A' includes the "access" permission and 'Role A' is associated with the dataset, only those users
                        and groups who are associated with 'Role A' may access the dataset.
                    </p>
                    <p>
                        If multiple roles that include the "access" permission are associated with a dataset, access to the dataset is derived
                        from the intersection of the users associated with the roles.  For example, if 'Role A' and 'Role B' are associated with
                        a dataset, only those users and groups who are associated with both 'Role A' AND 'Role B' may access the dataset.  When
                        the "access" permission is applied to a dataset, Galaxy checks to make sure that at least 1 user belongs to all groups and
                        roles associated with the "access" permission (otherwise the dataset would be restricted from everyone).
                    </p>
                    <p>
                        In order for a user to make a dataset private (i.e., only they can access it), they should associate the dataset with
                        their private role (the role identical to their Galaxy user name / email address).  Associating additional roles that
                        include the "access" permission is not possible, since it would render the dataset inaccessible to everyone.
                    <p>
                        To make a dataset private to themselves and one or more other users, the user can create a new role and associate the dataset 
                        with that role, not their "private role".  Galaxy makes this easy by telling the user they are about to share a private dataset 
                        and giving them the option of doing so.  If they respond positively, the sharing role is automatically created for them.
                    </p>
                    <p>
                        Private data (data associated with roles that include the "access" permission) must be made public in order to be used
                        with external applications like the "view at UCSC" link, or the "Perform genome analysis and prediction with EpiGRAPH" 
                        tool.  Being made publically accessible means removing the association of all roles that include the "access" permission
                        from the dataset.
                    <p>
                </li>
                <li><strong>manage permissions</strong> - Role members can manage the permissions applied to this dataset</li>
            </ul>
        </li>
    </ul>
    <br/>
%endif
