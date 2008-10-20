<%inherit file="/base.mako"/>

<%def name="title()">Galaxy Administration</%def>

<h2>Galaxy Administration</h2>

<p>Please choose an administration task from the menu on the left.</p>

<hr/>

<div class="toolHelp">
    <div class="toolHelpBody">
        <p class="infomark">Dataset security in Galaxy is complex.  Please familiarize yourself with the details before you begin.  The most important points are listed below.</p>
    </div>
</div>

<ul>
    <li>Anonymous users' data is always public.  Users must log in to access security controls.</li>
    <li>If no roles are set for the 'access' permission, the dataset is public, and anyone may access it.</li>
    <li>If no roles are set for the 'manage permissions' permission, no one (other than administrators) may modify its permissions.</li>
    <li>Adding roles to a dataset's 'access' permission restricts who may access it.  If 'Role A' is associated, only those users and groups who are associated with 'Role A' may access the dataset.  If 'Role A' and 'Role B' are associated with a dataset, only those users and groups who are associated with <strong>both 'Role A' AND 'Role B' may access the dataset.</strong></li>
    <li>To make a dataset private to just yourself, associate it with the role identical to your user name (email address).  <strong>Adding additional roles to the 'access' permission along with your "private role" does not do what you may expect: since roles are always logically ANDed together, only you will be able to access the dataset, since only you are a member of your "private role".</strong>  To make a dataset private to you and one or more other users, create a new role (note: this functionality is still under development) and associate the dataset with that role, not your "private role".</li>
    <li>Private data must be made public to be used with external sources, such as the "view at UCSC" link, or the "Perform genome analysis and prediction with EpiGRAPH" tool.</li>
</ul>

<p>Full details can be found in the <a href="http://g2.trac.bx.psu.edu/wiki/SecurityFeatures" target="_blank">Security Features page of the Galaxy Wiki</a>.</p>
