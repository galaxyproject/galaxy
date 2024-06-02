from galaxy.carbon_emissions import get_carbon_intensity_entry


def test_get_carbon_intensity_entry():
    """
    Test if `get_carbon_intensity_entry` retrieves the correct name and carbon
    intensity value for a country or region
    """
    country_entry = get_carbon_intensity_entry("US")
    region_entry = get_carbon_intensity_entry("US-NY")
    invalid_entry = get_carbon_intensity_entry("Raya Lucaria")

    assert country_entry["location_name"] == "United States of America"
    assert country_entry["carbon_intensity"] == 423.94

    assert region_entry["location_name"] == "New York (United States of America)"
    assert region_entry["carbon_intensity"] == 199.01

    assert invalid_entry["location_name"] == "GLOBAL"
    assert invalid_entry["carbon_intensity"] == 475.0
