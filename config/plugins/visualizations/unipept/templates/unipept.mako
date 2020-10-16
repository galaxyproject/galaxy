<%
    root = h.url_for( "/static/" )
    app_root = root + "plugins/visualizations/unipept/static/"
%>

<html>
  <meta charset="utf-8">

  <head>
    <title>Unipept Taxonomy Visualizer</title>

    <!-- font  -->
    <link href="https://fonts.googleapis.com/css?family=Roboto:400,400italic,300,500,700" rel="stylesheet" type="text/css">

    <!-- Jquery -->
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>

    <!-- D3 -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.6/d3.min.js"></script>

    <!-- Visualizations -->
    ${h.javascript_link( app_root + 'unipept-visualizations.es5.js' )}

    <!-- Stylesheet -->
    ${h.stylesheet_link( app_root + 'style.css' )}

    <script>
    $(document).ready(function() {

        $(".button").click(function(e) {
          // prevent bubble up or whatever
          e.preventDefault();

          // change button to active
          $(".button").removeClass("active");
          $(this).addClass("active");

          // change visible div
          $('.wrapper').hide();
          $('#' + $(this).data('rel')).show();
        });

        // reset button: not functional
        // $(".glyphicons-repeat").click(function(e) {
        //   e.preventDefault;
        //   $("#" + $(this).data('rel')).treemap.Constructor.reset();
        // });

        // initiate first click to hide other two visualizations
        $(".button[data-rel='treeview-wrapper']").trigger('click');

        d3.json("${h.url_for( controller='/datasets', action='index')}/${trans.security.encode_id( hda.id )}/display",
        function(error, data) {
          if (error) return console.warn(error);

          $("#treemap").treemap(data, {
            width: 798,
            height: 780,
            getTooltip: function(d) {
              let numberFormat = d3.format(",d");
              return "<b>" + d.name + "</b> (" + d.data.rank + ")<br/>" + numberFormat(!d.data.self_count ? "0" : d.data.self_count) + (d.data.self_count && d.data.self_count === 1 ? " sequence" : " sequences") +
                " specific to this level<br/>" + numberFormat(!d.data.count ? "0" : d.data.count) + (d.data.count && d.data.count === 1 ? " sequence" : " sequences") + " specific to this level or lower";
            }
          });
        });

        d3.json("${h.url_for( controller='/datasets', action='index')}/${trans.security.encode_id( hda.id )}/display",
        function(error, data) {
          if (error) return console.warn(error);

          $("#sunburst").sunburst(data, {
            width: 800,
            height: 800,
            radius: 400,
            getTooltip: function(d) {
              let numberFormat = d3.format(",d");
              return "<b>" + d.name + "</b> (" + d.data.rank + ")<br/>" + numberFormat(!d.data.self_count ? "0" : d.data.self_count) + (d.data.self_count && d.data.self_count === 1 ? " sequence" : " sequences") +
                " specific to this level<br/>" + numberFormat(!d.data.count ? "0" : d.data.count) + (d.data.count && d.data.count === 1 ? " sequence" : " sequences") + " specific to this level or lower";
            }
          });
        });

        d3.json("${h.url_for( controller='/datasets', action='index')}/${trans.security.encode_id( hda.id )}/display",
        function(error, data) {
          if (error) return console.warn(error);

          $("#treeview").treeview(data, {
            width: 800,
            height: 800,
            getTooltip: function(d) {
              let numberFormat = d3.format(",d");
              return "<b>" + d.name + "</b> (" + d.data.rank + ")<br/>" + numberFormat(!d.data.self_count ? "0" : d.data.self_count) + (d.data.self_count && d.data.self_count === 1 ? " sequence" : " sequences") +
                " specific to this level<br/>" + numberFormat(!d.data.count ? "0" : d.data.count) + (d.data.count && d.data.count === 1 ? " sequence" : " sequences") + " specific to this level or lower";
            }
          });
        });


      });
      </script>
  </head>



  <body>

    <div class="outer-frame">
      <div class="tab">
        <a class="button" href="#" data-rel="treeview-wrapper">Treeview</a>
        <a class="button" href="#" data-rel="sunburst-wrapper">Sunburst</a>
        <a class="button" href="#" data-rel="treemap-wrapper">Treemap</a>
      </div>

      <div class="inner-frame">

        <div class="content-container">
          <div id="sunburst-wrapper" class="wrapper">
            <h2 class="ghead">
              <span class="dirtext">
                Click a slice to zoom in and the center node to zoom out.
              </span>

              <!-- reset button, not working  -->
              <!-- <span class="glyphicons glyphicons-repeat" data-rel="sunburst">
                <img src="./glyphicons-86-repeat.png">
              </span> -->

            </h2>
              <div id="sunburst"></div>
          </div>

          <div id="treeview-wrapper" class="wrapper">
            <h2 class="ghead">
              <!-- reset button  -->
              <span class="dirtext">
                  Scroll to zoom, drag to pan, click a node to expand, right click a node to set as root
              </span>
              <!-- <span class="glyphicons glyphicons-repeat" data-rel="treeview">
                <img src="./glyphicons-86-repeat.png">
              </span> -->
            </h2>
            <div id="treeview"></div>
          </div>

          <div id="treemap-wrapper" class="wrapper">
            <h2 class="ghead">

              <span class="dirtext">
                  Click a square to zoom in and right click to zoom out
              </span>

              <!-- reset button  -->
              <!-- <span class="glyphicons glyphicons-repeat" data-rel="treemap">
                <img src="./glyphicons-86-repeat.png">
              </span> -->
            </h2>
            <div id="treemap"></div>
          </div>
        </div>
      </div>
    </div>
  </body>
  <footer>
  Visualizations use the Unipept stand-alone visualizations package, with code available
  <a href="https://github.com/unipept/unipept-visualizations" target = "_blank">here</a>
  </footer>
</html>
