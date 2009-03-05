$j.m( {
	Viewport: {
	  start: NaN,
	  end: NaN,
	  dbkey: "",
	  chrom: "",
  	  template: {},
	  tracks: []
	},
	Data: {
	  getDBKeys: function (callback) {
	    $j.m.Data.json("/tracks/dbkeys", function (response) {
	      for(item in response)
		$j.m.Data.dbkeys[response[item]] = {chroms: {}};
		  if($j.m.Viewport.dbkey == "")
		    $j.m.Viewport.dbkey = response[0];
	      if(callback) callback(response);
	    });
	  },
	  getDatasets: function (callback) {
	    $j.m.Data.json("/tracks/list?dbkey="+$j.m.Viewport.dbkey, function (response) {
	      $j.m.Data.datasets = response;
	      if(callback) callback(response);
	    });
	  },
	  getChroms: function (dbkey, callback) {
	    $j.m.Data.json("/tracks/chroms?dbkey="+dbkey, function (response) {
	      for( key in response) {
		if($j.m.Data.dbkeys[dbkey].chroms[key] == undefined) {
		  $j.m.Data.dbkeys[dbkey].chroms[key] = new Object();
		}
		$j.m.Data.dbkeys[dbkey].chroms[key].len = response[key];
	      }
	      if(callback) callback(response);
	    });
	  },
	  getData: function(dataset, chrom, start, end, callback) {
	    var qs = "/tracks/data";
	    qs += "?dataset_id=" + dataset.toString();
	    if(chrom != undefined) qs += "&chrom=" + chrom;
	    if(start != undefined) qs += "&start=" + start.toString();
	    if(end != undefined) qs += "&end=" + end.toString();
	    $j.m.Data.json(qs,
	    function (response) {
	      if($j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom] == undefined)
		$j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom] = new Object();
	      if(response.resolution) {
		if($j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom][dataset] == undefined)
		  $j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom][dataset] = new Object();
		$j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom][dataset][response.resolution] = response;
	      } else {
		$j.m.Data.dbkeys[$j.m.Viewport.dbkey].chroms[chrom][dataset] = response;
	      }
	      if(callback) callback(response);
	    });
	  },
	  getDataset: function(dataset, callback) {
	    var qs = "/tracks/data";
	    qs += "?dataset_id=" + dataset.toString();
	    $j.m.Data.json(qs,
	      function(response) {
		if(callback) callback(response);
	      });
	  },
	  dbkeys: {},
	  datasets: {}
	}
});
