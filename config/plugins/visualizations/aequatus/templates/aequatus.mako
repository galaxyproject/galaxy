<%
    default_title = "Aequatus of"

    # Use root for resource loading.
    root = h.url_for( '/static/' )
    app_root    = root + "plugins/visualizations/aequatus/static/"
%>
## ----------------------------------------------------------------------------

<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title> ${visualization_name}</title>

## external scripts
        ${h.javascript_link( app_root + "aequatus-vis/scripts/jquery/js/jquery-3.3.1.min.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/jquery/js/jquery-ui-1.12.1.min.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/jquery/js/jquery.cookie.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/jquery/js/jquery.svg.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/jquery/js/jquery-migrate-1.4.1.min.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/scriptaculous/prototype.js" )}


## install shared libraries
        ${h.js( 'libs/d3')}

## aequatus-vis
        ${h.javascript_link( app_root + "aequatus-vis/scripts/init.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/geneView.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/drawGene.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/drawGeneExonOnly.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/drawCIGARs.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/util.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/d3_tree.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/newick.js" )}
        ${h.javascript_link( app_root + "aequatus-vis/scripts/cigarUtils.js" )}


## aequatus plugin script
        ${h.javascript_link( app_root + "scripts/controls.js" )}
        ${h.javascript_link( app_root + "scripts/popup.js" )}


## external css
        ${h.stylesheet_link( app_root + "aequatus-vis/scripts/jquery/jquery-ui-1.12.1.min.css" )}
        ${h.stylesheet_link( app_root + "aequatus-vis/scripts/jquery/jquery.svg.css" )}
        ${h.stylesheet_link( app_root + "aequatus-vis/styles/font-awesome-5.6.1/css/fontawesome.min.css" )}
        ${h.stylesheet_link( app_root + "aequatus-vis/styles/font-awesome-5.6.1/css/solid.min.css" )}
        ${h.stylesheet_link( app_root + "aequatus-vis/styles/style.css" )}

## aequatus css
        ${h.stylesheet_link( app_root + "styles/aequatus.css" )}

## sql-js
        ${h.javascript_link( app_root + "scripts/sql.js" )}
        ${h.javascript_link( app_root + "scripts/readSQLite.js" )}
        ${h.javascript_link( app_root + "scripts/worker.sql.js" )}

</head>

## ----------------------------------------------------------------------------
<body style="cursor: auto; height: 100%; position: absolute; width: 100%; z-index: 1999;">

<script type="text/javascript">


    kickOff();

    var hda_id = '${ trans.security.encode_id( hda.id ) }'

    var ajax_url = "${h.url_for( controller='/datasets', action='index')}/" + hda_id + "/display"

    var json_result = setDB(ajax_url, get_Genes_for_family)

    function start(json){
        var syntenic_data = json

        init(syntenic_data, "#settings_div")

        drawTree(syntenic_data.tree, "#gene_tree", newpopup)
    }




</script>
<div id="control_panel">
    <table cellspacing="0" cellpadding="0" border="0">
        <tbody>
        <tr valign=top>
            <td width="300px" id=control_divs>


                <div id="search_div">
                    <div id="families">
                    </div>
                </div>

                <div id="settings_div">
                </div>

                <div id="info_div">
                    <table width="100%" cellpadding="5px">
                        <tbody>
                        <tr>
                            <td colspan="2" align="left"><b> Tree and Gene Legends </b></td>
                        </tr>
                        <tr>
                            <td align="right">
                                <div class="circleBase type2" style="background: red;"></div>
                            </td>
                            <td align="left">
                                Duplication
                            </td>
                        </tr>
                        <tr>
                            <td align="right">
                                <div class="circleBase type2" style="background: cyan;"></div>
                            </td>
                            <td align="left">
                                Dubious
                            </td>
                        </tr>
                        <tr>
                            <td align="right">
                                <div class="circleBase type2" style="background: blue"></div>
                            </td>
                            <td align="left">
                                Speciation
                            </td>
                        </tr>
                        <tr>
                            <td align="right">
                                <div class="circleBase type2" style="background: pink"></div>
                            </td>
                            <td align="left">
                                Gene Split
                            </td>
                        </tr>

                        <tr>
                            <td align="right">
                                <div class="circleBase type2" style="background: white; border: 2px solid blue;"></div>
                            </td>
                            <td align="left">
                                Multiple events
                            </td>
                        </tr>
                        <tr>
                            <td align="right">
                                <svg version="1.1" width="55" height="14">
                                    <line x1="0" y1="6" x2="55" y2="6" id="Examplegeneline" stroke="green" stroke-width="1"/>
                                    <g class="style2">
                                        <rect x="2" y="1" width="51.087" height="10" rx="2" ry="2" id="exampleExonstyle2" fill="white" stroke="green" stroke-width="2"/>
                                    </g>

                                    <g id="examplestyle2CIGAR" class="style2 CIGAR">
                                        <rect x="2" y="1" width="33" height="10" rx="1" ry="1" fill="gray" class="utr1"/>
                                        <rect x="34.005102040816325" y="1" width="18.994897959183675" height="10" rx="1" ry="1" fill="rgb(166,206,227)" class="match"/>
                                    </g>
                                </svg>
                            </td>
                            <td align="left">UTR
                            </td>
                        </tr>
                        </tbody>
                    </table>
                </div>
                <div style="display: none; background: none repeat scroll 0% 0% orange; padding: 10px; height: 248px; text-align: center; font-size: 16px;"
                     id="filter_div">
                    <b>Species list:</b>
                    <div id="filter"></div>
                    <div id="sliderfilter" style="text-align: left; margin-top: 10px">
                </div>
            </td>
            <td width="50px">
                <div id="control_panel_handle">
                    <b> ... </b>
                </div>

                <div id="search_div_handle" onclick="openPanel('#search_div')">
                    <i style="color: white; padding: 7px;" class="fas fa-search fa-2x"></i>
                </div>

                <div id="settings_div_handle" onclick="openPanel('#settings_div')" >
                    <i style="color: white; padding: 7px;" class="fas fa-cogs fa-2x"></i>
                </div>

                <div id="info_panel_handle" onclick="openPanel('#info_div')">
                    <i style="color: white; padding: 7px;" class="fas fa-info fa-2x"></i>
                </div>

                <div id="filter_handle" onclick="openPanel('#filter_div')">
                    <i style="color: white; padding: 7px;" class="fas fa-filter fa-2x"></i>
                </div>

                <div id="openclose_handle" onclick="openClosePanel('#settings_div')">
                    <i style="color: white; padding: 4px;" class="fas fa-exchange-alt fa-2x"> </i>
                </div>
            </td>
        </tr>
        </tbody>
    </table>
</div>


<div id="canvas">
    <div id="gene_tree">
    </div>
</div>


<div id="popup" class="bubbleright" >
    <div id="popup_header">
        <div id="stable_id_header">
            <span id="name_label">&nbsp;</span>
            <i onclick="removePopup();" class="fas fa-times "  style="color: white; position: absolute; right: 5px; cursor: pointer; "></i>
        </div>
    </div>
    <div id="popup_body">
        <table width="100%" cellspacing="0" border="0">
            <tbody>
            <tr>
                <td>
                    <div id="ref_name"></div>
                </td>
            </tr>
            <tr>
                <td>
                    <div id="position"></div>
                </td>
            </tr>

            <tr>
                <td>
                    <div id="gene_desc"></div>
                </td>
            </tr>
            <tr align="right">
                <td>
                    <table>
                        <tbody>
                        <tr>
                            <td>
                                <div id="makemetop_button"></div>
                            </td>
                        </tr>
                        </tbody>
                    </table>
                </td>
            </tr>
            </tbody>
        </table>
    </div>

</div>

<span id="ruler"></span>

</body>

</html>
