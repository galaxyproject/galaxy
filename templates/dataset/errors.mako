<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <title>Dataset generation errors</title>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <link href="/static/style/base.css" rel="stylesheet" type="text/css" />
        <style>
            pre
            {
                background: white;
                color: black;
                border: dotted black 1px;
                overflow: auto;
                padding: 10px;
            }
        </style>
    </head>

    <body>
        <h2>Dataset generation errors</h2>
        <p><b>Dataset ${hda.hid}: ${hda.display_name()}</b></p>

        %if hda.creating_job_associations:
            <% job = hda.creating_job_associations[0].job %>
            %if job.traceback:
                The Galaxy framework encountered the following error while attempting to run the tool:
                <pre>${job.traceback | h}</pre>
            %endif
            %if job.stderr or job.info:
                Tool execution generated the following error message:
                %if job.stderr:
                    <pre>${job.stderr | h}</pre>
                %elif job.info:
                    <pre>${job.info | h}</pre>
                %endif
            %else:
                Tool execution did not generate any error messages.
            %endif
            %if job.stdout:
                The tool produced the following additional output:
                <pre>${job.stdout | h}</pre>
            %endif
        %else:
            The tool did not create any additional job / error info.
        %endif
        <%
            if trans.user:
                user_email = trans.user.email
            else:
                user_email = ''
        %>
        <h2>Report this error to the Galaxy Team</h2>
        <p>
            The Galaxy team regularly reviews errors that occur in the application. 
            However, if you would like to provide additional information (such as 
            what you were trying to do when the error occurred) and a contact e-mail
            address, we will be better able to investigate your problem and get back
            to you.
        </p>
        <div class="toolForm">
            <div class="toolFormTitle">Error Report</div>
            <div class="toolFormBody">
                <form name="report_error" action="${h.url_for( action='report_error')}" method="post" >
                    <input type="hidden" name="id" value="${hda.id}" />
                    <div class="form-row">
                        <label>Your email</label>
                        <input type="text" name="email" size="40" value="${user_email}" />
                    </div>
                    <div class="form-row">
                        <label>Message</label>
                        <textarea name="message" rows="10" cols="40"></textarea>
                    </div>
                    <div class="form-row">
                        <input type="submit" value="Report"/>
                    </div>
                </form>
            </div>
      </div>
    </body>
</html>
