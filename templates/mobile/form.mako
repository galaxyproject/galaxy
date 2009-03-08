<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>${form.title}</title>
  <meta name="viewport" content="width=devicewidth; initial-scale=1.0; maximum-scale=1.0; user-scalable=0;"/>
  <link rel="apple-touch-icon" href="${h.url_for('/static/iui/iui-logo-touch-icon.png')}" />
  <meta name="apple-touch-fullscreen" content="YES" />
  <style type="text/css" media="screen">@import "${h.url_for('/static/style/iphone.css')}";</style>
  ## <script type="application/x-javascript" src="${h.url_for('/static/iui/iui.js')}"></script>
</head>

<body>
    <div class="toolbar">
        <h1 id="pageTitle">${form.title}</h1>
        <a id="backButton" class="button" href="#"></a>
    </div>
    
    <form title="${form.title}" class="panel" selected="true" name="${form.name}" action="${form.action}" method="post" >
        <fieldset>
        %for input in form.inputs:
            <%
            cls = "row"
            if input.error:
                cls += " form-row-error"
            %>
            <div class="${cls}">
              %if input.use_label:
              <label>
                  ${input.label}:
              </label>
              %endif
              <input type="${input.type}" name="${input.name}" value="${input.value}" size="40">
              %if input.error:
                  <div class="error">Error: ${input.error}</div>
              %endif
            </div>
            
        %endfor
        </fieldset>
      <input class="whiteButton" type="submit" value="${form.submit_text}">

  </form>
  </div>
</div>
