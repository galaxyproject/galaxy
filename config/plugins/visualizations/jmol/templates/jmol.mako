<%
    import os
    hdadict = trans.security.encode_dict_ids( hda.to_dict() )
    root     = h.url_for( '/' )
    j2s = h.url_for("/static/plugins/visualizations/jmol/static/j2s")
    jsmol = h.url_for("/static/plugins/visualizations/jmol/static/JSmol.min.js")
    file_url ="load " + os.path.join(root, 'datasets', hdadict['id'], "display?to_ext="+".cif")
%>

<!DOCTYPE html>
<html>
<head>
<title>Super-Simple JSmol</title>
<meta charset="utf-8">

</head>
<body>
<script type="text/javascript" src="${jsmol}"></script>
<script type="text/javascript">


Info = {
    width: window.innerWidth*.8,
    height: window.innerHeight*.8,
	debug: false,
    j2sPath: '${j2s}',
	color: "0xC0C0C0",
	addSelectionOptions: false,
	use: "HTML5",
	readyFunction: null,
    bondWidth: 4,
    zoomScaling: 1.5,
    pinchScaling: 2.0,
    mouseDragFactor: 0.5,
    touchDragFactor: 0.15,
    multipleBondSpacing: 4,
    spinRateX: 0.2,
    spinRateY: 0.5,
    spinFPS: 20,
    spin:false,
    debug: false
}

jmolApplet0 = Jmol.getApplet("jmolApplet0", Info);
Jmol.script(jmolApplet0, "${file_url}");

</script>
</body>


</html>
