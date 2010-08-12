##
## Generate the XML for a myExperiment 'upload workflow' request.
##
<%!
    from xml.sax.saxutils import escape
    import textwrap, base64 
%>

## Generate request.
<?xml version="1.0"?>
<workflow>
  <title>${workflow_name}</title>
  <description>${workflow_description}</description>
  <type>Galaxy</type>
  <content encoding="base64" type="binary">
      ${textwrap.fill( base64.b64encode( workflow_content ), 64 )}
  </content>
  <preview encoding="base64" type="binary">
  </preview>
</workflow>