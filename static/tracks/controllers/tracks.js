$j.c( {
	/**
	 * Viewport controller
	 *
	 **/
	Viewport: {
	  index: function () {

	    this.loadDBKeys();

	    $j.v.Viewport.initTemplates();
	    $j.v.Viewport.initWindow();
	    $j.v.Viewport.initTracks();
	    $j.v.Viewport.initHistoryPanel();
	    this._registerListeners();

	    // initialize axis
	    $j.m.xAxis =  new Axis();
	  },
	  /**
	   * Register Listeners
	   * @access private
	   **/
	  _registerListeners: function() {
	    $("a#show-history").bind("click", $j.v.Viewport.showHistory);
	    $("a#hide-history").bind("click", $j.v.Viewport.hideHistory);
	    $("select#dbkey").bind( "change", this.setDBKey );
	    $("select#chrom").bind( "change", this.setChrom );
	    $(window).bind("resize", this.redrawTracks );

	  },
	  loadDBKeys: function() {
	    $j.m.Data.getDBKeys( function() {
	      $j.v.Viewport.showDBKeys();
	    });
	  },
	  setDBKey: function(e) {
	    $j.m.Viewport.dbkey = e.target.value;
	    $j.m.Data.getDatasets( function() {
	      // Setup history
	      $j.v.Viewport.showDatasets();
	    });
	    $j.c.Viewport.getChroms();
	  },
	  getChroms: function() {
	    $j.m.Data.getChroms( $j.m.Viewport.dbkey, function() {
	      $j.v.Viewport.showChroms();
	    });
	  },
	  setChrom: function(e) {
	    chrom = $j.m.Viewport.chrom = e.target.value;
	    if( $j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom]) {
	      $j.m.Viewport.start = 0;
	      $j.m.Viewport.end = $j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom].len;
	    } else {
	      $j.m.Viewport.start = NaN;
	      $j.m.Viewport.end = NaN;
	    }
	    // Update data shown
	    for( track in $j.m.Viewport.tracks ) {
	      var trackObj = $j.m.Viewport.tracks[track];
	      $j.m.Data.getData(trackObj.datasetId, $j.m.Viewport.chrom, $j.m.Viewport.start, $j.m.Viewport.end, function(response) {
		$j.m.Viewport.tracks[track].redraw();
	      });
	    }
	    $j.m.xAxis.redraw();
	  },
	  addTrack: function(datasetId) {
	    // Add a dataset track to the MVC
	    // Drop->receive->initTrack->this->$j.v.Viewport.addTrack
	    var newTrack = new Track(datasetId);
	    $j.log(datasetId);
	    var loadTrack = function () {
	      $j.m.Data.getDataset( datasetId, function(response) {
		if( response=="data" ) {
		  if( $j.m.Viewport.chrom=="" ) $j.v.Viewport.getChroms();
		  else $j.m.Data.getData( datasetId,
		    $j.m.Viewport.chrom,
		    $j.m.Viewport.start,
		    $j.m.Viewport.end, function(t) {
		      return function() {
			t.redraw();
		      }
		    }(newTrack));
		} else if (response=="pending") {
		  setTimeout(loadTrack, 8000);
		}
	      });
	    }
	    loadTrack();
	    $j.m.Viewport.tracks.push( newTrack );
	    $j.v.Viewport.addTrack( newTrack );
	    newTrack.redraw();
	  },
	  removeDataset: function(e) {
	    // TODO: Remove a dataset from the MVC
	  },
	  panTo: function(e) {
	    // TODO: Pan.
	  },
	  panBy: function(delta) {
	    $j.m.Viewport.start += delta;
	    $j.m.Viewport.end += delta;
	    $j.c.Viewport.redrawTracks();
	  },
	  zoomIn: function(e) {
	    var range = $j.m.Viewport.end - $j.m.Viewport.start;
	    $j.m.Viewport.end -= range / 4;
	    $j.m.Viewport.start += range / 4;
	    $j.c.Viewport.redrawTracks();
	  },
	  zoomTo: function(e) {
	    // TODO: zoom
	  },
	  redrawTracks: function(e) {
	    for( track in $j.m.Viewport.tracks ) {
		$j.m.Viewport.tracks[track].redraw();
	    }
	    $j.m.xAxis.redraw();
	  }
	}
  }
);
