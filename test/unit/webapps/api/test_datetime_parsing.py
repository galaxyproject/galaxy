from pydantic import BaseModel

from galaxy.schema.types import OffsetNaiveDatetime


class Time(BaseModel):
    time: OffsetNaiveDatetime


def test_naive_datetime_parsing():
    with_zulu = Time(time="2022-08-15T11:29:32.853974Z")
    without_zulu = Time(time="2022-08-15T11:29:32.853974")
    assert with_zulu.time == without_zulu.time
    assert not with_zulu.time.tzinfo
