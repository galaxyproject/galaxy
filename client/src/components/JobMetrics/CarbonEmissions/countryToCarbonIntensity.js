// Country/Region names are given as ISO 3166 codes

const africa = [
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "ZA",
    name: "South Africa",
    carbonIntensity: 900.6,
  },
]

const asia = [
  // source: https://energypedia.info/wiki/Energy_Transition_in_Taiwan
  {
    location: "TW",
    name: "Taiwan",
    carbonIntensity: 509,
  },
  // source: https://www.electricitymap.org
  {
    location: "IL",
    name: "Israel",
    carbonIntensity: 558,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "CN",
    name: "China",
    carbonIntensity: 537.4,
  },
  // source: carbonfootprint (March 2022) and Hong Kong Electric Company (2020) (data from 2020)
  {
    location: "CN-HK",
    name: "Hong Kong (HK Electricity Company)",
    carbonIntensity: 710,
  },
  // source: carbonfootprint (March 2022) and CLP Group (2020) (data from 2020)
  {
    location: "CN-HK2",
    name: "Hong Kong (CLP Group)",
    carbonIntensity: 650,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "IN",
    name: "India",
    carbonIntensity: 708.2,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "ID",
    name: "Indonesia",
    carbonIntensity: 717.7,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "JP",
    name: "Japan",
    carbonIntensity: 465.8,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "KR",
    name: "Korea",
    carbonIntensity: 415.6,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "SA",
    name: "Saudi Arabia",
    carbonIntensity: 505.9,
  },
  // source: carbonfootprint (March 2022) and Singapore Energy Market Authority (EMA) (data from 2020)
  {
    location: "SG",
    name: "Singapore",
    carbonIntensity: 408,
  },
  // source: carbonfootprint (March 2022) and Energy Policy and Planning Office (EPPO) Thai Government Ministry of Energy (data from 2020)
  {
    location: "TH",
    name: "Thailand",
    carbonIntensity: 481,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "TR",
    name: "Turkey",
    carbonIntensity: 375,
  },
  // source: carbonfootprint (March 2022) and Dubai Electricity & Water Authority (sustainability report 2020) (data from 2020)
  {
    location: "AE",
    name: "United Arab Emirates",
    carbonIntensity: 417.89,
  },
] 

const europe = [
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "AT",
    name: "Austria",
    carbonIntensity: 111.18,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "BE",
    name: "Belgium",
    carbonIntensity: 161.89,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "BG",
    name: "Bulgaria",
    carbonIntensity: 372.12,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "HR",
    name: "Croatia",
    carbonIntensity: 226.96,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "CY",
    name: "Cyprus",
    carbonIntensity: 642.9,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "CZ",
    name: "Czech Republic",
    carbonIntensity: 495.49,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "DK",
    name: "Denmark",
    carbonIntensity: 142.52,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "EE",
    name: "Estonia",
    carbonIntensity: 598.69,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "FI",
    name: "Finland",
    carbonIntensity: 95.32,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "FR",
    name: "France",
    carbonIntensity: 51.28,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "DE",
    name: "Germany",
    carbonIntensity: 338.66,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "GR",
    name: "Greece",
    carbonIntensity: 410.01,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "HU",
    name: "Hungary",
    carbonIntensity: 243.75,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "IS",
    name: "Iceland",
    carbonIntensity: 0.13,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "IE",
    name: "Ireland",
    carbonIntensity: 335.99,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "IT",
    name: "Italy",
    carbonIntensity: 323.84,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "LV",
    name: "Latvia",
    carbonIntensity: 215.67,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "LT",
    name: "Lithuania",
    carbonIntensity: 253.56,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "LU",
    name: "Luxembourg",
    carbonIntensity: 101.36,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "MT",
    name: "Malta",
    carbonIntensity: 390.62,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "NL",
    name: "Netherlands",
    carbonIntensity: 374.34,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "NO",
    name: "Norway",
    carbonIntensity: 7.62,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "PL",
    name: "Poland",
    carbonIntensity: 759.62,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "PT",
    name: "Portugal",
    carbonIntensity: 201.55,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "RO",
    name: "Romania",
    carbonIntensity: 261.84,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "RU",
    name: "Russian Federation",
    carbonIntensity: 310.2,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "RS",
    name: "Serbia",
    carbonIntensity: 776.69,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "SK",
    name: "Slovakia",
    carbonIntensity: 155.48,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "SI",
    name: "Slovenia",
    carbonIntensity: 224.05,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "ES",
    name: "Spain",
    carbonIntensity: 171.03,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "SE",
    name: "Sweden",
    carbonIntensity: 5.67,
  },
  // source: carbonfootprint (March 2022) and Association of Issuing Bodies (AIB) 2021 (data from 2020)
  {
    location: "CH",
    name: "Switzerland",
    carbonIntensity: 11.52,
  },
  // source: carbonfootprint (March 2022) and UK Govt - Defra/BEIS 2021 (report from 2021 using 2019/20 data)
  {
    location: "GB",
    name: "United Kingdom",
    carbonIntensity: 231.12,
  },
]

const northAmerica = [
  // source: carbonfootprint (March 2022) and UN Framework Convention on Climate Change (report from 2021 based on 2019 data)
  {
    location: "CA",
    name: "Canada",
    carbonIntensity: 120,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-AB",
    name: "Alberta (Canada)",
    carbonIntensity: 670,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-BC",
    name: "British Columbia (Canada)",
    carbonIntensity: 19.7,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-MT",
    name: "Manitoba (Canada)",
    carbonIntensity: 1.3,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-NB",
    name: "New Brunswick (Canada)",
    carbonIntensity: 270,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-NL",
    name: "Newfoundland and Labrador (Canada)",
    carbonIntensity: 29,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-NS",
    name: "Nova Scotia (Canada)",
    carbonIntensity: 810,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-NT",
    name: "Northwest Territories (Canada)",
    carbonIntensity: 200,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-NU",
    name: "Nunavut (Canada)",
    carbonIntensity: 900,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-ON",
    name: "Ontario (Canada)",
    carbonIntensity: 30,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-PE",
    name: "Prince Edward Island (Canada)",
    carbonIntensity: 2,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-QC",
    name: "Quebec (Canada)",
    carbonIntensity: 1.5,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-SK",
    name: "Saskatchewan (Canada)",
    carbonIntensity: 710,
  },
  // source: carbonfootprint (March 2022) and Canada's submission to UN Framework convention on Climate Change (2021) (data from 2019 published in 2021)
  {
    location: "CA-YT",
    name: "Yukon Territory (Canada)",
    carbonIntensity: 111,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "MX",
    name: "Mexico",
    carbonIntensity: 431.4,
  },
  // source: carbonfootprint (March 2022) and US Env Protection Agency (EPA) eGrid (data from 2019)
  {
    location: "US",
    name: "United States of America",
    carbonIntensity: 423.94,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-AK",
    name: "Alaska (USA)",
    carbonIntensity: 462.33,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-AL",
    name: "Alabama (USA)",
    carbonIntensity: 344.37,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-AR",
    name: "Arkansas (USA)",
    carbonIntensity: 454.4,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-AZ",
    name: "Arizona (USA)",
    carbonIntensity: 351.99,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-CA",
    name: "California (USA)",
    carbonIntensity: 216.43,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-CO",
    name: "Colorado (USA)",
    carbonIntensity: 582.34,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-CT",
    name: "Connecticut (USA)",
    carbonIntensity: 253,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-DC",
    name: "Washington DC (USA)",
    carbonIntensity: 382.68,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-DE",
    name: "Delaware (USA)",
    carbonIntensity: 360.68,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-FL",
    name: "Florida (USA)",
    carbonIntensity: 402.2,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-GA",
    name: "Georgia (USA)",
    carbonIntensity: 345.58,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-HI",
    name: "Hawaii (USA)",
    carbonIntensity: 731.21,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-IA",
    name: "Iowa (USA)",
    carbonIntensity: 293.85,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-ID",
    name: "Idaho (USA)",
    carbonIntensity: 101.89,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-IL",
    name: "Illinois (USA)",
    carbonIntensity: 265.8,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-IN",
    name: "Indiana (USA)",
    carbonIntensity: 740.02,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-KS",
    name: "Kansas (USA)",
    carbonIntensity: 384.08,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-KY",
    name: "Kentucky (USA)",
    carbonIntensity: 804.75,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-LA",
    name: "Louisiana (USA)",
    carbonIntensity: 363.82,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-MA",
    name: "Massachusetts (USA)",
    carbonIntensity: 420.32,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-MD",
    name: "Maryland (USA)",
    carbonIntensity: 308.21,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-ME",
    name: "Maine (USA)",
    carbonIntensity: 109,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-MI",
    name: "Michigan (USA)",
    carbonIntensity: 448.08,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-MN",
    name: "Minnesota (USA)",
    carbonIntensity: 367.93,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-MO",
    name: "Missouri (USA)",
    carbonIntensity: 773,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-MS",
    name: "Mississip (USA)",
    carbonIntensity: 427.07,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-MT",
    name: "Montana (USA)",
    carbonIntensity: 435.87,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-NC",
    name: "North Carolina (USA)",
    carbonIntensity: 309.73,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-ND",
    name: "North Dakota (USA)",
    carbonIntensity: 663.05,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-NE",
    name: "Nebraska (USA)",
    carbonIntensity: 573.51,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-NH",
    name: "New Hampshire (USA)",
    carbonIntensity: 118.44,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-NJ",
    name: "New Jersey (USA)",
    carbonIntensity: 235.1,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-NM",
    name: "New Mexico (USA)",
    carbonIntensity: 601.77,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-NV",
    name: "Nevada (USA)",
    carbonIntensity: 342.25,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-NY",
    name: "New York (USA)",
    carbonIntensity: 199.01,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-OH",
    name: "Ohio (USA)",
    carbonIntensity: 598.58,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-OK",
    name: "Oklahoma (USA)",
    carbonIntensity: 338.44,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-OR",
    name: "Oregon (USA)",
    carbonIntensity: 163.15,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-PA",
    name: "Pennsylvania (USA)",
    carbonIntensity: 333.19,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-RI",
    name: "Rhode Island (USA)",
    carbonIntensity: 395.27,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-SC",
    name: "South Carolina (USA)",
    carbonIntensity: 245.48,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-SD",
    name: "South Dakota (USA)",
    carbonIntensity: 162.69,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-TN",
    name: "Tennessee (USA)",
    carbonIntensity: 272.89,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-TX",
    name: "Texas (USA)",
    carbonIntensity: 409.16,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-UT",
    name: "Utah (USA)",
    carbonIntensity: 747.82,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-VA",
    name: "Virginia (USA)",
    carbonIntensity: 308,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-VT",
    name: "Vermont (USA)",
    carbonIntensity: 14.45,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-WA",
    name: "Washington (USA)",
    carbonIntensity: 101.84,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-WI",
    name: "Wisconsin (USA)",
    carbonIntensity: 569.39,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-WV",
    name: "West Virginia (USA)",
    carbonIntensity: 919.34,
  },
  // source: carbonfootprint (March 2022) (data from 2020 published in 2022)
  {
    location: "US-WY",
    name: "Wyoming (USA)",
    carbonIntensity: 950.5,
  },
]

const oceania = [
  // source: carbonfootprint (June 2022 v1.1) and Australian Government (data from 2019 published in August 2021)
  {
    location: "AU",
    name: "Australia",
    carbonIntensity: 840,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-ACT",
    name: "Australian Capital Territory (Australia)",
    carbonIntensity: 870,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-NSW",
    name: "New South Wales (Australia)",
    carbonIntensity: 870,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-NT",
    name: "Northern Territory (Australia)",
    carbonIntensity: 620,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-QLD",
    name: "Queensland (Australia)",
    carbonIntensity: 920,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-SA",
    name: "South Australia (Australia)",
    carbonIntensity: 420,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-TAS",
    name: "Tasmania (Australia)",
    carbonIntensity: 180,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-VIC",
    name: "Victoria (Australia)",
    carbonIntensity: 1060,
  },
  // source: carbonfootprint (March 2022) and the Australian government (data from 2019 published in 2021)
  {
    location: "AU-WA",
    name: "Western Australia (Australia)",
    carbonIntensity: 580,
  },
  // source: carbonfootprint (March 2022) and Ministry for the Environment https://www.mfe.govt.nz/node/18670/ (data from 2018)
  {
    location: "NZ",
    name: "New Zealand",
    carbonIntensity: 110.1,
  },
]

const southAmerica = [
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "AR",
    name: "Argentina",
    carbonIntensity: 307,
  },
  // source: carbonfootprint (March 2022) and Climate Transparency (2021 Report) (data from 2020)
  {
    location: "BR",
    name: "Brazil",
    carbonIntensity: 61.7,
  },
  // source: https://app.electricitymaps.com/zone/UY
  {
    location: "UY",
    name: "Uruguay",
    carbonIntensity: 129,
  }
]

export const countryCarbonIntensity = [
  // source: https://www.iea.org/reports/global-energy-co2-status-report-2019/emissions
  {
    location: "GLOBAL",
    name: "Global",
    carbonIntensity: 475,
  },
  ...africa,
  ...asia,
  ...europe,
  ...northAmerica,
  ...oceania,
  ...southAmerica
]
