// dependencies
define([], function() {

// color palettes
var colorSets = {
    seis:       ['#AA0000', '#D00000', '#F70000', '#FF1D00', '#FF4400', '#FF6A00', '#FF9000', '#FFB700', '#FFDD00', '#FFFF00', '#FFFF00', '#FFFF00', '#BDFF0C', '#73FF1A', '#3FFA36', '#16F45A', '#00D08B', '#0087CD', '#0048FA', '#0024E3'].reverse(),
    
    sealand:    ['#8C66FF', '#6A66FF', '#6684FF', '#66A7FF', '#66CAFF', '#66ECFF', '#66FFF0', '#66FFCE', '#66FFAB', '#66FF88', '#66FF66', '#88FF66', '#ABFF66', '#CEFF66', '#FFEEA6', '#FFD3A6', '#FFB8A6', '#FFAAB0', '#FFB5CB', '#FFC0E1'].reverse(),
    
    redgreen:   ['#005824', '#1A693B', '#347B53', '#4F8D6B', '#699F83', '#83B09B', '#9EC2B3', '#B8D4CB', '#D2E6E3', '#EDF8FB', '#FFFFFF', '#F1EEF6', '#E6D3E1','#DBB9CD', '#D19EB9', '#C684A4', '#BB6990', '#B14F7C', '#A63467', '#9B1A53', '#91003F'],
    
    ocean:      ['#000000', '#000209', '#000413', '#00061E', '#000728', '#000932', '#002650', '#00426E', '#005E8C', '#007AAA', '#0096C8', '#22A9C2', '#45BCBB', '#67CFB5', '#8AE2AE', '#ACF6A8', '#BCF8B9', '#CBF9CA', '#DBFBDC', '#EBFDED'].reverse(),
    
    cool:       ['#00FFFF', '#0DF2FF', '#19E6FF', '#26D9FF', '#33CCFF', '#3FBFFF', '#4CB3FF', '#59A6FF', '#6699FF', '#738CFF', '#7F7FFF', '#8C73FF', '#9966FF', '#A659FF', '#B24DFF', '#BF3FFF', '#CC33FF', '#D926FF', '#E619FF', '#F20DFF'],
    
    copper:     ['#000000', '#100906', '#1F130D', '#301E13', '#40281A', '#50321F', '#603C26', '#70462D', '#805033', '#905A3A', '#A06440', '#B06E46', '#C0784D', '#D08253', '#E08C5A', '#F09660', '#FFA066', '#FFAA6D', '#FFB473', '#FFBE7A'].reverse(),
    
    gray:       ['#000000', '#0D0D0D', '#191919', '#262626', '#333333', '#3F3F3F', '#4C4C4C', '#595959', '#666666', '#737373', '#7F7F7F', '#8C8C8C', '#999999', '#A6A6A6', '#B2B2B2', '#BFBFBF', '#CCCCCC', '#D9D9D9', '#E6E6E6', '#F2F2F2'].reverse(),
    
    hot:        ['#000000', '#220000', '#440000', '#660000', '#880000', '#AA0000', '#CC0000', '#EE0000', '#FF1100', '#FF3300', '#FF5500', '#FF7700', '#FF9900', '#FFBB00', '#FFDD00', '#FFFF00', '#FFFF33', '#FFFF66', '#FFFF99', '#FFFFCC'].reverse(),
    
    jet:        ['#00007F', '#0000B2', '#0000E5', '#0019FF', '#004DFF', '#007FFF', '#00B2FF', '#00E5FF', '#FFFFF2', '#FFFFD9', '#FFFFBF', '#FFFFA5', '#FFFF8C', '#FFE500', '#FFB300', '#FF7F00', '#FF4C00', '#FF1900', '#E50000', '#B20000'],
    
    no_green:   ['#1F60FF', '#1F60FF', '#1F9FFF', '#1FBFFF', '#00CFFF', '#2AFFFF', '#2AFFFF', '#55FFFF', '#7FFFFF', '#AAFFFF', '#FFFF54', '#FFFF54', '#FFF000', '#FFBF00', '#FFA800', '#FF8A00', '#FF8A00', '#FF7000', '#FF4D00', '#FF0000'],

    polar:      ['#0000FF', '#1919FF', '#3333FF', '#4C4CFF', '#6666FF', '#7F7FFF', '#9999FF', '#B2B2FF', '#CCCCFF', '#E6E6FF', '#FFFFFF', '#FFE5E5', '#FFCCCC', '#FFB2B2', '#FF9999', '#FF7F7F', '#FF6666', '#FF4C4C', '#FF3333', '#FF1A1A'],

    red2green:  ['#FF0000', '#FF1919', '#FF3333', '#FF4C4C', '#FF6666', '#FF7F7F', '#FF9999', '#FFB2B2', '#FFCCCC', '#FFE6E6', '#FFFFFF', '#E5FFE5', '#CCFFCC', '#B2FFB2', '#99FF99', '#7FFF7F',  '#66FF66', '#4CFF4C', '#33FF33', '#1AFF1A'].reverse(),

    relief:     ['#000000', '#000413', '#000728', '#002650', '#005E8C', '#0096C8', '#45BCBB', '#8AE2AE', '#BCF8B9', '#DBFBDC', '#467832', '#887438', '#B19D48', '#DBC758', '#FAE769', '#FAEB7E', '#FCED93', '#FCF1A7', '#FCF6C1', '#FDFAE0'].reverse(),
    
    split:      ['#7F7FFF', '#6666E6', '#4D4DCC', '#3333B3', '#1A1A99', '#00007F', '#000066', '#00004D', '#000033', '#00001A', '#000000', '#1A0000', '#330000', '#4D0000', '#660000', '#7F0000', '#991A1A', '#B33333', '#CC4D4D', '#E66666'],
    
    wysiwyg:    ['#3F003F', '#3F003F', '#3F00BF', '#003FFF', '#00A0FF', '#3FBFFF', '#3FBFFF', '#40E0FF', '#3FFFBF', '#3FFF3F', '#7FFF3F', '#BFFF3F', '#BFFF3F', '#FFE040', '#FFE040', '#FF6040', '#FF1F40', '#FF60C0', '#FFA0FF', '#FFA0FF'].reverse()
}

// return
return {
    colorSets: colorSets
}

});