from collections import namedtuple
import json

class ShotDetectionSchema:
    def __init__(self, media = None, shots = None):
        self.shots = []
        if media is None:
            self.media = ShotDetectionMediaSchema()
        else:
             self.media = media
        if shots is None:
            self.shots = []
        else:
             self.shots = shots
             
class ShotDetectionMediaSchema:
    filename = ""
    duration = 0

    def __init__(self, filename = "", duration = 0):
        self.filename = filename
        self.duration = duration

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)

class ShotDetectionShotSchema:
    type = ""
    start = 0
    end = 0
    
    def __init__(self, type = "", start = 0, end = 0):
        self.type = type
        self.start = start
        self.end = end

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)


