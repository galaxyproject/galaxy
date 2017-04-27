<%!
def inputs(form_args):
    """
    Creates list of input elements
    """
    element = ""
    for name, value in form_args.items():
        element += "<input type=\"hidden\" name=\"%s\" value=\"%s\"/>" % (name,
                                                                          value)
    return element
%>

<html>
  <head>
    <title>Submit This Form</title>
  </head>
  <body onload="javascript:document.forms[0].submit()">
    <form method="post" action=${action}>
        ${inputs(form_args)}
    </form>
  </body>
</html>
