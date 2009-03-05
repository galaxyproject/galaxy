$j.v({
	/**
	 * Class Track
	 * Track in contianer
	 **/
	Tracks: {
		children:[],
		init: function(curAddition) {
		  var curTemplate = $j.v.Viewport.trackTemplate.clone();

     	  $(curTemplate).attr("id", "item_" + $("#tracks-sortable > li").length);
     	  $(curTemplate).find(".track-title").html(curAddition.find(".history-item-title > b").html());
		  return curTemplate;
		}
	} // end class Track
});