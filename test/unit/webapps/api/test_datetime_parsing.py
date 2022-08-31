from pydantic import BaseModel

from galaxy.schema.types import OffsetNaiveDatetime


class Time(BaseModel):
    time: OffsetNaiveDatetime


def test_naive_datetime_parsing():
    with_tz = Time(time="2022-08-15T11:29:32.853974+02:00")
    without_tz = Time(time="2022-08-15T09:29:32.853974")
    assert with_tz.time == without_tz.time
    assert with_tz.time.tzinfo is None
