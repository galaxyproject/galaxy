const appElement = document.querySelector("#app");

const incoming = JSON.parse(document.getElementById("app").dataset.incoming);

const HDA_ID = incoming.visualization_config.dataset_id;
const APP_ROOT = `${incoming.root}static/plugins/visualizations/aequatus/static/`;
const AJAX_URL = `${incoming.root}api/datasets/${HDA_ID}/display`;

function appendStyle(path) {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = APP_ROOT + path;
    document.head.appendChild(link);
}

function appendScript(path) {
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = APP_ROOT + path;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

function loadStyles() {
    appendStyle("aequatus-vis/scripts/jquery/jquery-ui-1.12.1.min.css");
    appendStyle("aequatus-vis/scripts/jquery/jquery.svg.css");
    appendStyle("aequatus-vis/styles/font-awesome-5.6.1/css/fontawesome.min.css");
    appendStyle("aequatus-vis/styles/font-awesome-5.6.1/css/solid.min.css");
    appendStyle("aequatus-vis/styles/style.css");
    appendStyle("styles/aequatus.css");
}

async function loadScripts() {
    await appendScript("aequatus-vis/scripts/jquery/js/jquery-3.3.1.min.js");
    await appendScript("aequatus-vis/scripts/jquery/js/jquery-ui-1.12.1.min.js");
    await appendScript("aequatus-vis/scripts/jquery/js/jquery.cookie.js");
    await appendScript("aequatus-vis/scripts/jquery/js/jquery.svg.js");
    await appendScript("aequatus-vis/scripts/jquery/js/jquery-migrate-1.4.1.min.js");
    await appendScript("aequatus-vis/scripts/scriptaculous/prototype.js");
    await appendScript("scripts/d3.min.js");
    await appendScript("aequatus-vis/scripts/init.js");
    await appendScript("aequatus-vis/scripts/geneView.js");
    await appendScript("aequatus-vis/scripts/drawGene.js");
    await appendScript("aequatus-vis/scripts/drawGeneExonOnly.js");
    await appendScript("aequatus-vis/scripts/drawCIGARs.js");
    await appendScript("aequatus-vis/scripts/util.js");
    await appendScript("aequatus-vis/scripts/d3_tree.js");
    await appendScript("aequatus-vis/scripts/newick.js");
    await appendScript("aequatus-vis/scripts/cigarUtils.js");
    await appendScript("scripts/controls.js");
    await appendScript("scripts/popup.js");
    await appendScript("scripts/sql.js");
    await appendScript("scripts/readSQLite.js");
    await appendScript("scripts/worker.sql.js");
}

(function injectMarkup() {
    const container = document.createElement("div");
    container.innerHTML = `
        <div id="control_panel">
            <table cellspacing="0" cellpadding="0" border="0">
                <tbody>
                <tr valign="top">
                    <td width="300px" id="control_divs">
                        <div id="search_div"><div id="families"></div></div>
                        <div id="settings_div"></div>
                        <div id="info_div">
                            <table width="100%" cellpadding="5px">
                                <tbody>
                                <tr><td colspan="2"><b> Tree and Gene Legends </b></td></tr>
                                <tr><td align="right"><div class="circleBase type2" style="background: red;"></div></td><td>Duplication</td></tr>
                                <tr><td align="right"><div class="circleBase type2" style="background: cyan;"></div></td><td>Dubious</td></tr>
                                <tr><td align="right"><div class="circleBase type2" style="background: blue;"></div></td><td>Speciation</td></tr>
                                <tr><td align="right"><div class="circleBase type2" style="background: pink;"></div></td><td>Gene Split</td></tr>
                                <tr><td align="right"><div class="circleBase type2" style="background: white; border: 2px solid blue;"></div></td><td>Multiple events</td></tr>
                                <tr>
                                    <td align="right">
                                        <svg version="1.1" width="55" height="14">
                                            <line x1="0" y1="6" x2="55" y2="6" stroke="green" stroke-width="1"/>
                                            <g class="style2">
                                                <rect x="2" y="1" width="51.087" height="10" rx="2" ry="2" fill="white" stroke="green" stroke-width="2"/>
                                            </g>
                                            <g class="style2 CIGAR">
                                                <rect x="2" y="1" width="33" height="10" rx="1" ry="1" fill="gray" class="utr1"/>
                                                <rect x="34.005" y="1" width="19" height="10" rx="1" ry="1" fill="rgb(166,206,227)" class="match"/>
                                            </g>
                                        </svg>
                                    </td>
                                    <td>UTR</td>
                                </tr>
                                </tbody>
                            </table>
                        </div>
                        <div id="filter_div" style="display: none; background: orange; padding: 10px; height: 248px; text-align: center; font-size: 16px;">
                            <b>Species list:</b>
                            <div id="filter"></div>
                            <div id="sliderfilter" style="text-align: left; margin-top: 10px"></div>
                        </div>
                    </td>
                    <td width="50px">
                        <div id="control_panel_handle"><b> ... </b></div>
                        <div id="search_div_handle" onclick="openPanel('#search_div')"><i class="fas fa-search fa-2x" style="color: white; padding: 7px;"></i></div>
                        <div id="settings_div_handle" onclick="openPanel('#settings_div')"><i class="fas fa-cogs fa-2x" style="color: white; padding: 7px;"></i></div>
                        <div id="info_panel_handle" onclick="openPanel('#info_div')"><i class="fas fa-info fa-2x" style="color: white; padding: 7px;"></i></div>
                        <div id="filter_handle" onclick="openPanel('#filter_div')"><i class="fas fa-filter fa-2x" style="color: white; padding: 7px;"></i></div>
                        <div id="openclose_handle" onclick="openClosePanel('#settings_div')"><i class="fas fa-exchange-alt fa-2x" style="color: white; padding: 4px;"></i></div>
                    </td>
                </tr>
                </tbody>
            </table>
        </div>
        <div id="canvas"><div id="gene_tree"></div></div>
        <div id="popup" class="bubbleright">
            <div id="popup_header">
                <div id="stable_id_header">
                    <span id="name_label">&nbsp;</span>
                    <i onclick="removePopup();" class="fas fa-times" style="color: white; position: absolute; right: 5px; cursor: pointer;"></i>
                </div>
            </div>
            <div id="popup_body">
                <table width="100%" cellspacing="0" border="0">
                    <tbody>
                    <tr><td><div id="ref_name"></div></td></tr>
                    <tr><td><div id="position"></div></td></tr>
                    <tr><td><div id="gene_desc"></div></td></tr>
                    <tr align="right"><td><table><tr><td><div id="makemetop_button"></div></td></tr></table></td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        <span id="ruler"></span>
    `;
    document.body.appendChild(container);
})();

(async function initializeAequatus() {
    loadStyles();
    await loadScripts();

    kickOff();
    setDB(AJAX_URL, get_Genes_for_family);

    window.start = function(json) {
        const syntenic_data = json;
        init(syntenic_data, "#settings_div");
        drawTree(syntenic_data.tree, "#gene_tree", newpopup);
    };
})();
