$j.v({
     Viewport: {
       addView: function(dataset_id) {
         // $("#viewport").append($j.m.Viewport.TrackTemplate.clone());
         // $("div.track:last").attr("id", this.get_tid(dataset_id));
       },
       renderView: function(dataset_id) {
         if (!$(this.get_selector(dataset_id)).length)
           this.addView(dataset_id);
       },
       get_selector: function(dataset_id) {
         return "div.track[@id=" + this.get_tid(dataset_id) + "]";
       },
       get_tid: function(dataset_id) {
         return "t" + dataset_id.toString();
       },
	   showDBKeys: function() {
	     options = '';
	     for( key in $j.m.Data.dbkeys ) {
	       options += '<option value="'+key+'">'+key+'</option>';
	     }
	     $("select#dbkey").html(options);
	     $("select#dbkey option:first").change();
	   },
	   showChroms: function() {
	     options = '';
	     for( key in $j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms ) {
	       options += '<option value="'+key+'">'+key+"</option>";
	     }
	     $("select#chrom").html(options);
	     $("select#chrom option:first").change();
	   },
	   showDatasets: function() {
	     options = '';
	     for( key in $j.m.Data.datasets ) {
	       options += '<option value="'+$j.m.Data.datasets[key]+'">'+key+"</option>";
	     }
	     $("select#datasets").html(options);
	   },
       initTracks: function() {
         $("#tracks-sortable").sortable({
           handle: ".track-label",
           items: 'li',
		   receive: function( event, ui ) {
			currentAddition = $(".track-history-item"); // only one history added at one time.
	 		$j.v.Viewport.addTrack(currentAddition);
			//  on recieve of item from history list
		   }
	     });
	     return false;
       },
	   addTrack: function(curAddition) {
		 var curTemplate = $j.m.Viewport.template.clone();
		
		 $(curTemplate).attr("id", "item_" + $("#tracks-sortable > li").length);
		 $(curTemplate).find(".track-title").html(curAddition.find(".history-item-title > b").html());
		 
		 $("#tracks-sortable .track-history-item:last").remove();
		 $("#tracks-sortable").append(curTemplate);
	   },
	   removeTrack:function() {
			
	   },
	   populateTrack: function() {
		 
	   },
	   initHistoryPanel: function() {
		 //$("#drag-history").css("display", "none");
		 $("#tracks-history-sortable").sortable({
           handle: ".history-item",
		   connectWith: $("#tracks-sortable"),
           items: 'li',
		   remove: function( event, ui ) {
			// on remove from history list
		   }
	     });
	   },
	   initOdometer: function() {

	     $("#macro-slider").slider({
	       range:true,
	       min: 0,
	       max: 100,
	       orientation: 'horizontal',
	       values:[20, 80],
	       start: function( event, ui ) {
	         // do blur tracks, odometers
	       },
	       slide: function( event, ui ) {
	         $j.log( "slide range: " + $(this).slider("values", 0) + " :: " + $(this).slider("values", 1) );
	       },
	       stop: function( event, ui ) {
//	         $j.log( "range: " + $(this).slider("values", 0) + " :: " + $(this).slider("values", 1) );
	        // $("#micro-scroll-bar").trigger("scroll");
	       }
	     });
         

		// $("#macro-slider").bind("mousedown", function( event ) {
		// 	if(e.pageX > $("#macro-slider").slider("values", 0) && e.pageX > $("#macro-slider").slider("values", 1) ) {
		// 		$j.log("mouse down");
		// 	}
		// });
	     // $( "#micro-scroll-bar" ).bind("scroll", function( event ) {
	     // 	       num = Math.floor ( Math.random() * 100 );
	     // 	       $( "#micro-scroll-bar" ).slider('option', 'value', num);
	     // 	       $( "#micro-scroll-content" ).css("margin-left", $("#micro-scroll-content").width() * -(num/100));
	     // 	     });
	     // 
	     // 	     $( "#micro-scroll-bar" ).slider({
	     // 		   orientation: 'horizontal',
	     // 		   start: function( event, ui ) {
	     // 		   // do blur tracks, odometers
	     // 		   },
	     // 		   slide: function( event, ui ) {
	     // 		     scrollContent = $("#micro-scroll-content");
	     // 		     scrollPane = $("#micro-scroll-pane");
	     // 			 if( scrollContent.width() > scrollPane.width() ) { 
	     // 			   scrollContent.css('margin-left', Math.round( ui.value / 100 * ( scrollPane.width() - scrollContent.width() )) + 'px'); 
	     // 			 }
	     // 			 else { 
	     // 			   scrollContent.css('margin-left', 0); 
	     // 			 }				
	     // 		   },
	     // 		   change: function( event, ui ) {
	     // 					// set new positions
	     // 					$j.log("end: " + ui.value);				
	     // 		   }
	     // 		  });
		  this.updateOdometer();
		},
		updateOdometer: function() {
			$j.log("updating odoemeter");
		}
    }
});