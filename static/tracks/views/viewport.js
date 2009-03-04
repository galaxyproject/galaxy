$j.v({
	/**
	 * Class Viewport
	 * Entire container
	 **/
	 Viewport: {
       addView: function(dataset_id) {
         // $("#viewport").append($j.m.Viewport.TrackTemplate.clone());
         // $("div.track:last").attr("id", this.get_tid(dataset_id));
       },
       initTemplates: function () {
	 this.historyTemplate = $(".track-history-item").remove();
	 this.trackTemplate = $(".track-list-item").remove();
       },
       showDBKeys: function() {
	 var options = '';
	 for( key in $j.m.Data.dbkeys ) {
	   options += '<option value="'+key+'">'+key+'</option>';
	 }
	 $("select#dbkey").html(options);
	 $("select#dbkey option:first").change();
       },
       showChroms: function() {
	 var options = '';
	 for( key in $j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms ) {
	   options += '<option value="'+key+'">'+key+"</option>";
	 }
	 $("select#chrom").html(options);
	 $("select#chrom option:first").change();
       },
       showDatasets: function() {
	 for( dataset in $j.m.Data.datasets ) {
	   var newDataset = $(this.historyTemplate).clone();
	   $("#tracks-history-sortable").append(newDataset);
	   var title = dataset.toString()+": "+$j.m.Data.datasets[dataset];
	   newDataset.find(".history-item-title > b").html(title);
	   newDataset.bind("initTrack", function (d) {
	     return function() {
	       $("#tracks-sortable .track-history-item:last").remove();
	       $j.c.Viewport.addTrack(d);
	       return false;
	     };
	   }(dataset));
	 }
       },
       initTracks: function() {
         $j.log("initializing tracks");
         $("#tracks-sortable").sortable({
           handle: ".track-label",
           items: 'li',
		   over: function( event, ui ) {
		     $("#tracks-sortable").css("border", "2px solid #FFee44");
		   },
		   receive: function( event, ui ) {
		     $("#tracks-sortable").css("border", "none");
		     $("#tracks-sortable .track-history-item:last").trigger("initTrack");
		   },
		   stop: function( event, ui ) {
		     $("#tracks-sortable").css("border", "none");
		   }
	     });
	     return false;
       },
       showHistory: function() {
	 $("#viewport").css("width", "80%");
	 $("#drag-history").css("width", "19%");
	 $("#drag-history").css("visibility", "visible");
       },
       hideHistory: function() {
	 $("#viewport").css("width", "100%");
	 $("#drag-history").css("visibility", "hidden");
       },
       addTrack: function(curAddition) {
	 //var newTrack = $j.v.Tracks.init(curAddition);

	 $("#tracks-sortable").append(curAddition.elem);
       },
       removeTrack:function(curRemoval) {
	 curRemoval.remove();
       },
       populateTrack: function() {

       },
       initHistoryPanel: function() {
	 $("#tracks-history-sortable").sortable({
	   handle: ".history-item",
	   connectWith: $("#tracks-sortable"),
       items: 'li',
	   remove: function( event, ui ) {
	     // on remove from history list
	   }
	 });
	 this.hideHistory();
       },
       initWindow: function() {
		  $("#macro-slider").css("background", "#e6e7e8");
		  $("#macro-slider").append("<div id='macro-handle'></div>");
		  $("#macro-handle").css("width", "20%");
		  $("#macro-handle").css("height", "100%");
		  $("#macro-handle").css("background", "#cc0000");
		},
		updateOdometer: function() {
			$j.log("updating odoemeter");
		}

    } // end class Viewport
});