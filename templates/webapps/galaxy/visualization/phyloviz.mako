<%inherit file="/webapps/galaxy/base_panels.mako"/>
##
<%def name="init()">
    <%
        self.has_left_panel=False
        self.has_right_panel=False
        self.active_view="visualization"
        self.message_box_visible=False
    %>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>

        .node circle {
            cursor: pointer;
            fill: #fff;
            stroke: steelblue;
            stroke-width: 1.5px;
        }

        .node.searchHighlight circle {
            stroke-width: 3px;
            stroke: #7adc26;
        }

        .node.selectedHighlight circle {
            stroke-width: 3px;
            stroke: #dc143c;
        }

        path.link {
            fill: none;
            stroke: #B5BBFF;
            stroke-width: 4.0px;
        }


        div #phyloVizNavContainer{
            text-align: center;
            width: 100%;
            height: 0px;
        }

        div #phyloVizNav{
            font-weight: bold;
            display: inline-block;
            background: transparent;
            top: -2em;
            position: relative;
        }

        div .navControl{
            float: left;
        }

        div#FloatingMenu {
            left: 0;
            top: 15%;
            width:20%;
            z-index:100;
            padding: 5px;

        }

        div#SettingsMenu {
            width: 25%;
            top: 350px;

        }

        div#nodeSelectionView {
            width: 25%;
            top:70px;
        }

        .Panel {
            right: 0%;
            z-index: 101;
            position: fixed;

        ##          Borrowed from galaxy modal_dialogues
            background-color: white;
            border: 1px solid #999;
            border: 1px solid rgba(0, 0, 0, 0.3);
            -webkit-border-radius: 6px;
            -moz-border-radius: 6px;
            border-radius: 6px;
            -webkit-border-radius: 6px;
            -moz-border-radius: 6px;
            border-radius: 6px;
            -webkit-box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
            -moz-box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
            box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
            -webkit-box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
            -moz-box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
            box-shadow: 0 3px 7px rgba(0, 0, 0, 0.3);
            -webkit-background-clip: padding-box;
            -moz-background-clip: padding-box;
            background-clip: padding-box;
            -webkit-background-clip: padding-box;
            -moz-background-clip: padding-box;
            background-clip: padding-box;
        }

        span.PhylovizCloseBtn{
            cursor: pointer;
            float : right;
        }

        #PhyloViz{
            width: 100%;
            height: 95%;
        }

        h2.PhyloVizMenuTitle{
            color: white;
        }

        ##        Settings Menu
        .SettingMenuRows{
                    margin: 2px 0 2px 0;
                }


        ##        Helper Styles
        .PhyloVizFloatLeft{
                    float : left;
                }
        .icon-button.zoom-in,.icon-button.zoom-out{display:inline-block;height:16px;width:16px;margin-bottom:-3px;cursor:pointer;}
        .icon-button.zoom-out{background:transparent url(../images/fugue/magnifier-zoom-out.png) center center no-repeat;}
        .icon-button.zoom-in{margin-left:10px;background:transparent url(../images/fugue/magnifier-zoom.png) center center no-repeat;}

    </style>
</%def>


<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/require" )}

    <script type="text/javascript">

        require.config({
            baseUrl: "${h.url_for('/static/scripts')}",
            shim: {
                "libs/underscore": { exports: "_" },
                "libs/d3": { exports: "d3" }
            }
        });

        require(["viz/phyloviz"], function(phyloviz_mod) {

            function initPhyloViz(data, config) {
                var phyloviz;

                // -- Initialization code |-->
                phyloviz = new phyloviz_mod.PhylovizView({
                    data    : data,
                    layout  : "Linear",
                    config  :  config
                });

                // -- Render viz. --
                phyloviz.render();

            };

            $(function firstVizLoad(){       // calls when viz is loaded for the first time
                var config = ${ h.dumps( config )};
                var data = ${h.dumps(data['data'])};
                initPhyloViz(data, config);
            });
        });

    </script>
</%def>



<%def name="center_panel()">

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float:left;" id="title"></div>
            <div style="float:right;" id="panelHeaderRightBtns"></div>
        </div>
        <div style="clear: both"></div>
    </div>

    <div id="phyloVizNavContainer">
        <div id="phyloVizNav">
            %if config["ext"] == "nex" and not config["saved_visualization"]:
                <div id = "phylovizNexInfo" class="navControl">
                <p>Select a tree to view: &nbsp;&nbsp;
                <select id="phylovizNexSelector">
                    % for tree, index in data["trees"]:
                        <option value="${index}">${tree}</option>
                    % endfor
                </select>
                </p>
                </div>
            %endif
            <div id="phyloVizNavBtns" class="navControl">
            </div>
            <div class="navControl">
                <p>&nbsp;| Alt+click to select nodes</p>
            </div>
        </div>
    </div>

    ##  Node Selection Menu
    <div id="nodeSelectionView" class="Panel">
        <div class="modal-header">
            <h3 class="PhyloVizMenuTitle">Search / Edit Nodes :
                <span class="PhylovizCloseBtn" id="nodeSelCloseBtn"> X </span>
            </h3>
        </div>

        <div class="modal-body">

            <div class="SettingMenuRows">
                Search for nodes with:
                <select id="phyloVizSearchCondition" style="width: 55%">
                    <option value="name-containing">Name (containing)</option>
                    <option value="annotation-containing">Annotation (containing)</option>
                    <option value="dist-greaterEqual">Distance (>=)</option>
                    <option value="dist-lesserEqual">Distance (<=)</option>
                </select>
                <input  type="text" id="phyloVizSearchTerm" value="None" size="15" displayLabel="Distance">

                <div class="SettingMenuRows" style="text-align: center;">
                    <button id="phyloVizSearchBtn" > Search! </button>
                </div>
            </div>

            <br/>

            <div class="SettingMenuRows">
                Name: <input type="text" id="phyloVizSelectedNodeName" value="None" size="15" disabled="disabled" >
            </div>
            <div class="SettingMenuRows">
                Dist: <input type="text" id="phyloVizSelectedNodeDist" value="None" size="15" disabled="disabled" displayLabel="Distance">
            </div>
            <div class="SettingMenuRows">
                Annotation:
                <textarea id="phyloVizSelectedNodeAnnotation" disabled="disabled" ></textarea>
            </div>
            <div class="SettingMenuRows">
                Edit: <input type="checkbox" id="phylovizEditNodesCheck" value="You can put custom annotations here and it will be saved">
                <button id="phylovizNodeSaveChanges" style="display: none;"> Save edits</button>
                <button id="phylovizNodeCancelChanges" style="display: none;"> Cancel</button>
            </div>
        </div>
    </div>

    ##  Settings Menus
    <div id="SettingsMenu" class="Panel">
        <div class="modal-header">
            <h3 class="PhyloVizMenuTitle">Phyloviz Settings:
                <span class="PhylovizCloseBtn" id="settingsCloseBtn"> X </span>
            </h3>
        </div>
        <div class="modal-body">
            <div class="SettingMenuRows">
                Phylogenetic Spacing (px per unit): <input id="phyloVizTreeSeparation" type="text" value="250" size="10" displayLabel="Phylogenetic Separation"> (50-2500)
            </div>
            <div class="SettingMenuRows">
                Vertical Spacing (px): <input type="text" id="phyloVizTreeLeafHeight" value="18" size="10" displayLabel="Vertical Spacing"> (5-30)
            </div>
            <div class="SettingMenuRows">
                Font Size (px): <input type="text" id="phyloVizTreeFontSize" value="12" size="4" displayLabel="Font Size"> (5-20)
            </div>

        </div>
        <div class="modal-footer">
            <button id="phylovizResetSettingsBtn" class="PhyloVizFloatLeft" > Reset </button>
            <button id="phylovizApplySettingsBtn" class="PhyloVizFloatRight" > Apply </button>
        </div>
    </div>

    <div class="Panel" id="FloatingMenu" style="display: None;">

        <h2>PhyloViz (<a onclick="displayHelp()" href="javascript:void(0);">?</a>)</h2>
        <div style="display: none;">
            <h2>Summary of Interactions and Functions:</h2>
            <div class="hint">1. Expansion of Nodes: click or option-click to expand or collapse</div>
            <div class="hint">2. Zooming and translation: mousewheel, buttons, click and drag, double click. Reset</div>
            <div class="hint">3. Tooltip: Displays "Name and Size" on mouseOver on nodes</div>
            <div class="hint">4. Minimap: Currently displays an exact but scaled down replicate of the tree, orange bounding box is correct for linear only<br/>
                Can be switched on or off</div>
            <div class="hint">5. Changing Layouts: Able to change between circular and linear layouts.</div>
        </div>

        <h5>Scaling & Rotation:</h5>
        <button id="phylovizZoomInBtn" class="" > + </button>
        <button id="phylovizZoomOutBtn" class="" > - </button>

        <h5>Translation:</h5>
        <button id="phylovizTranslateUpBtn" > Up </button>
        <button id="phylovizTranslateDownBtn" > Down </button>
        <br/>
        <button id="phylovizTranslateLeftBtn" > Left </button>
        <button id="phylovizTranslateRightBtn" > Right </button>

        <h5>Others:</h5>
        <button id="phylovizResetBtn" > Reset Zoom/Translate </button>
        <button id="phylovizSaveBtn" > Save vizualization </button>
        <button id="phylovizOpenSettingsBtn" > Settings </button>
    </div>

    <div id="PhyloViz" >
    </div>

</%def>


