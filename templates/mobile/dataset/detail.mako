<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Galaxy</title>
  <meta name="viewport" content="width=devicewidth; initial-scale=1.0; maximum-scale=1.0; user-scalable=0;"/>
  <meta name="apple-touch-fullscreen" content="YES" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <style type="text/css" media="screen">@import "${h.url_for('/static/style/iphone.css')}";</style>
</head>

<body>
    <div class="toolbar masthead">
        <h1><img style="vertical-align: -5px;" src="${h.url_for("/static/images/galaxyIcon_noText.png")}"> Galaxy mobile</h1>
    </div>
    <div class="toolbar">
        <h1 id="pageTitle">${dataset.hid}: ${dataset.display_name()}</h1>
        <a id="backButton" class="button" href="${h.url_for( action='history_detail', id=dataset.history.id )}" style="display: block;">History</a>
    </div>

    <div class="panel" selected="true">
      <fieldset>
      <div class="row">
	<label>State</label> <span>${dataset.state}</span>
      </div>
      <div class="row">
	<label>Content</label> <span>${dataset.blurb}</span>
      </div>
      <div class="row">
        <label>Format</label> <span>${dataset.ext}</span>
      </div>
      <div class="row">
	<label>Info</label>
	<span>
	${dataset.display_info()}
	</span>
      </div>
      %if dataset.state == "ok":
      <div class="row">
	<label>Peek</label>
	<div style="padding: 12px 10px 0 110px;">
	${dataset.display_peek()}
	</div>
      </div>
      %endif
      </fieldset>
 
</body>
