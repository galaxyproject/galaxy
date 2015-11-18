<%inherit file="/base.mako"/>
    ${parent.stylesheets()}
    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            <table border="0">
                    %for i, tutorial in enumerate( tutorials ):
                        <tr>
                            <td>
                                <a href="/?tutorial_url=${tutorial.filename}" target="_parent">
                                    <div class="fa fa-car" href="#"> ${tutorial.description}</div>
                                </a>
                            </td>
                            <!--td>
                                <a class="action-button"
                                onclick="start_tutorial_from_url('${h.url_for(controller='page', action='get_tutorial_content', tutorial_config_file=tutorial.filename)}')"
                                href="javascript:void(0);">${tutorial.description}</a>
                            </td-->

                        </tr>
                    %endfor
            </table>
        </div>
    </div>
