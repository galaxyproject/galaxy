<!DOCTYPE html>

<%inherit file="base.mako"/>

<%block name="title">
    Unauthorized
    ${parent.title()}
</%block>

<%block name="headline">
    <!-- Static navbar -->
    <nav class="navbar navbar-default" role="navigation">
        <div class="navbar-header">
          <a class="navbar-brand" href="#">Unauthorized</a>
        </div>
    </nav>
</%block>

<%block name="body">
        <div class="row" style="text-align: center">
            <div class="col-lg-12">${message}</div>
        </div>
</%block>