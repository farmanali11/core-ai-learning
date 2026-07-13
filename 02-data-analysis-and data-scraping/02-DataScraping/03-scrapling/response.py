"""
Offline test for parse_result() using a real response shape captured from
postcodes.io's own published documentation (api.postcodes.io/postcodes bulk
endpoint). This validates the field mapping without needing live network
access to api.postcodes.io.
"""

from exercisetry import parse_result, PostcodeDemographics

# Real example payload shape, taken from postcodes.io's official docs
# (https://postcodes.io/docs/postcode/schema/), for SW1A 1AA.
SAMPLE_RAW = {
    "postcode": "SW1A 1AA",
    "quality": 1,
    "eastings": 529090,
    "northings": 179645,
    "country": "England",
    "nhs_ha": "London",
    "longitude": -0.141563,
    "latitude": 51.50101,
    "european_electoral_region": "London",
    "primary_care_trust": "Westminster",
    "region": "London",
    "lsoa": "Westminster 018C",
    "msoa": "Westminster 018",
    "incode": "1AA",
    "outcode": "SW1A",
    "parliamentary_constituency": "Cities of London and Westminster",
    "admin_district": "Westminster",
    "parish": "Westminster, unparished area",
    "admin_county": "(pseudo) England (UA/MD/LB)",
    "index_of_multiple_deprivation": 24862,
    "admin_ward": "St James's",
    "ccg": "NHS North West London",
    "nuts": "Westminster",
    "pfa": "Metropolitan Police",
    "ttwa": "London",
    "bua": "London",
}


def test_parse_result_maps_all_expected_fields():
    record = parse_result(SAMPLE_RAW, "SW1A 1AA")

    assert isinstance(record, PostcodeDemographics)
    assert record.postcode == "SW1A 1AA"
    assert record.status == "ok"
    assert record.country == "England"
    assert record.region == "London"
    assert record.admin_district == "Westminster"
    assert record.admin_ward == "St James's"
    assert record.lsoa == "Westminster 018C"
    assert record.msoa == "Westminster 018"
    assert record.index_of_multiple_deprivation == 24862
    assert record.parliamentary_constituency == "Cities of London and Westminster"
    assert record.nhs_health_authority == "London"
    assert record.ccg == "NHS North West London"
    assert record.police_force_area == "Metropolitan Police"
    assert record.built_up_area == "London"
    assert record.travel_to_work_area == "London"
    assert record.latitude == 51.50101
    assert record.longitude == -0.141563
    print("PASS: all fields mapped correctly")


def test_parse_result_handles_empty_string_as_none():
    raw = dict(SAMPLE_RAW)
    raw["admin_county"] = ""  # postcodes.io sometimes returns "" for unset values
    record = parse_result(raw, "SW1A 1AA")
    assert record.admin_county is None
    print("PASS: empty string normalized to None")


if __name__ == "__main__":
    test_parse_result_maps_all_expected_fields()
    test_parse_result_handles_empty_string_as_none()
    print("\nAll offline tests passed.")