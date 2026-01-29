# Carbon Emissions Reporting

Galaxy can estimate the carbon footprint of each job you run. The carbon emissions reporting can be 
configured for each galaxy instance to allow for more accurate results. The following options can
be set:

* [Geographical server location](#geographical-server-location)
* [Power usage effectiveness (PUE)](#power-usage-effectiveness)
* [Carbon emissions reporting toggle](#feature-toggling)

These calculations are based off of the work of the [Green Algorithms Project](https://www.green-algorithms.org/)
and in particular their implementation of the "carbon footprint calculator".
Additionally, some of our carbon emissions comparisons are based off of calculations done by the
United States [Environmental Protection Agency (EPA)](https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator).

## Geographical server location
The `geographical_server_location_code` flag is an [ISO 3166-2](https://en.wikipedia.org/wiki/ISO_3166-2) string specifying the
location of your galaxy instance, with the only exception being `GLOBAL`, which specifies that global average values are to be used.
Each valid code corresponds to a location name and a specific carbon intensity value. The corresponding flags 
(`geographical_server_location_name` and `carbon_intensity`) are automatically set and will be displayed to the client when carbon 
emissions are reported. The more accurate the location the better the estimates. In all cases, it is assumed that all jobs are run on
a server in the same location as the one specified in `geographical_server_location_code`.

[A list of supported locations can be found here.](#supported-locations)

## Power usage effectiveness
[Power usage effectiveness](https://en.wikipedia.org/wiki/Power_usage_effectiveness), or PUE for short, is a ratio specifying
how efficiently the data centre hosting your galaxy server used energy. It is essentially your server's 'indirect' energy usage.
Galaxy uses a default PUE of `1.67`. If you would like to set a custom value, you can [calculate a PUE value as follows](https://en.wikipedia.org/wiki/Power_usage_effectiveness).

## Feature toggling
The `carbon_emission_estimates` flag can be set to either `true` to enable carbon emissions reporting or `false` to
disable it altogether.

## Supported locations

Galaxy supports locations in the following sub-divisions
* [Africa](#africa)
* [Asia](#asia)
* [Europe](#europe)
* [North America](#north-america)
* [Oceania](#oceania)
* [South America](#south-america)

The only exception to the code format is for the 'global' location:
 - `GLOBAL` - The entire world.

### Africa
 - `ZA` - South Africa

### Asia
 - `AE` - United Arab Emirates
 - `CN-HK2` - Hong Kong (CLP Group)
 - `CN-HK` - Hong Kong (HK Electricity Company)
 - `CN`- China
 - `ID` - Indonesia
 - `IL`- Israel
 - `IN` - India
 - `JP` - Japan
 - `KR` - South Korea
 - `SA` - Saudi Arabia
 - `SG` - Singapore
 - `TH` - Thailand
 - `TR` - Turkey
 - `TW`- Taiwan

### Europe
- `AT` - Austria
- `BE` - Belgium
- `BG` - Bulgaria
- `CH` - Switzerland
- `CY` - Cyprus
- `CZ` - Czech Republic
- `DE` - Germany
- `DK` - Denmark
- `EE` - Estonia
- `ES` - Spain
- `FI` - Finland
- `FR` - France
- `GB` - United Kingdom
- `GR` - Greece
- `HR` - Croatia
- `HU` - Hungary
- `IE` - Ireland
- `IS` - Iceland
- `IT` - Italy
- `LT` - Lithuania
- `LU` - Luxembourg
- `LV` - Latvia
- `MT` - Malta
- `NL` - Netherlands
- `NO` - Norway
- `PL` - Poland
- `PT` - Portugal
- `RO` - Romania
- `RS` - Serbia
- `RU` - Russian Federation
- `SE` - Sweden
- `SI` - Slovenia
- `SK` - Slovakia

### Oceania
- `AU-ACT` - Australia (Australian Capital Territory)
- `AU-NSW` - Australia (New South Wales)
- `AU-NT2` - Australia (Northern Territory, Darwin Katherine Interconnected System)
- `AU-NT` - Australia (Northern Territory)
- `AU-QLD` - Australia (Queensland)
- `AU-SA` - Australia (South Australia)
- `AU-TAS` - Australia (Tasmania)
- `AU-VIC` - Australia (Victoria)
- `AU-WA1` - Australia (Western Australia, North Western Interconnected System)
- `AU-WA2` - Australia (Western Australia, South West Interconnected System)
- `AU` - Australia
- `NZ` - New Zealand

### North America
- `CA` - Canada
- `CA-AB` - Canada (Alberta)
- `CA-BC` - Canada (British Columbia)
- `CA-MT` - Canada (Manitoba)
- `CA-NB` - Canada (New Brunswick)
- `CA-NL` - Canada (Newfoundland and Labrador)
- `CA-NS` - Canada (Nova Scotia)
- `CA-NT` - Canada (Northwest Territories)
- `CA-NU` - Canada (Nunavut)
- `CA-ON` - Canada (Ontario)
- `CA-PE` - Canada (Prince Edward Island)
- `CA-QC` - Canada (Quebec)
- `CA-SK` - Canada (Saskatchewan)
- `CA-YT` - Canada (Yukon Territory)
- `MX` - Mexico
- `US` - USA
- `US-AK` - USA (Alaska)
- `US-AL` - USA (Alabama)
- `US-AR` - USA (Arkansas)
- `US-AZ` - USA (Arizona)
- `US-CA` - USA (California)
- `US-CO` - USA (Colorado)
- `US-CT` - USA (Connecticut)
- `US-DC` - USA (Washington DC)
- `US-DE` - USA (Delaware)
- `US-FL` - USA (Florida)
- `US-GA` - USA (Georgia)
- `US-HI` - USA (Hawaii)
- `US-IA` - USA (Iowa)
- `US-ID` - USA (Idaho)
- `US-IL` - USA (Illinois)
- `US-IN` - USA (Indiana)
- `US-KS` - USA (Kansas)
- `US-KY` - USA (Kentucky)
- `US-LA` - USA (Louisiana)
- `US-MA` - USA (Massachusetts)
- `US-MD` - USA (Maryland)
- `US-ME` - USA (Maine)
- `US-MI` - USA (Michigan)
- `US-MN` - USA (Minnesota)
- `US-MO` - USA (Missouri)
- `US-MS` - USA (Mississippi)
- `US-MT` - USA (Montana)
- `US-NC` - USA (North Carolina)
- `US-ND` - USA (North Dakota)
- `US-NE` - USA (Nebraska)
- `US-NH` - USA (New Hampshire)
- `US-NJ` - USA (New Jersey)
- `US-NM` - USA (New Mexico)
- `US-NV` - USA (Nevada)
- `US-NY` - USA (New York)
- `US-OH` - USA (Ohio)
- `US-OK` - USA (Oklahoma)
- `US-OR` - USA (Oregon)
- `US-PA` - USA (Pennsylvania)
- `US-RI` - USA (Rhode Island)
- `US-SC` - USA (South Carolina)
- `US-SD` - USA (South Dakota)
- `US-TN` - USA (Tennessee)
- `US-TX` - USA (Texas)
- `US-UT` - USA (Utah)
- `US-VA` - USA (Virginia)
- `US-VT` - USA (Vermont)
- `US-WA` - USA (Washington)
- `US-WI` - USA (Wisconsin)
- `US-WV` - USA (West Virginia)
- `US-WY` - USA (Wyoming)

### South America
- `AR` - Argentina
- `BR` - Brazil
- `UY` - Uruguay

