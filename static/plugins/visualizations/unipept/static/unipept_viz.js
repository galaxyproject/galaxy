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
        width: 800,
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
      d3.select('sunburst').attr("transform", "translate(400, 400)");
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
