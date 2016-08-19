define( [], function() {
    return [
        {   label : 'Default', value: 'default',
            help  : 'The visualizations below were curated from different libraries. Its a representative set covering most use cases. Use this selection by default.' },
        {   label : 'NVD3',    value: 'nvd3',
            help  : 'NVD3 is a popular d3-based library hosted at <a href="http://www.nvd3.org" target="_blank">www.nvd3.org<a/>. Most visualization types support intuitive drag-and-drop zooming and scaling. NVD3 generates high quality vector graphics. As with all vector based plugins, you may experience a slow down in browser responsiveness if visualizing thousands of data points.' },
        {   label : 'jqPlot',  value: 'jqplot',
            help  : 'jqPlot is a canvas-based library hosted at <a href="http://www.jqplot.com" target="_blank">www.jqplot.com<a/>. It is a plotting and charting plugin for the jQuery Javascript framework. Since based on canvas it is capable of rendering many thousand data points without adverse effects.' },
        {   label : 'Others',  value: 'others',
            help  : 'These visualizations were developed by the Galaxy team.'
        }
    ];
});