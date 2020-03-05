from collections import namedtuple
import json

class VideoOcrSchema:
    def __init__(self, media=None, frames = []):
        self.frames = []
        if media is None:
            self.media = VideoOcrMediaSchema()
        else:
             self.media = media
             


class VideoOcrResolutionSchema:
    width = None
    height = None
    frames = []
    def __init__(self, width = None, height = None):
        self.width = width
        self.height = height

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)

class VideoOcrMediaSchema:
    filename = ""
    duration = 0
    framerate = None
    numFrames = None
    resolution = VideoOcrResolutionSchema()

    def __init__(self, duration = 0, filename = "", framerate = None, numFrames = None, resolution = None):
        self.duration = duration
        self.filename = filename
        self.framerate = framerate
        self.numFrames = numFrames
        self.resolution = resolution

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)

class VideoOcrFrameSchema:
    start = 0
    boundingBoxes = []
    def __init__(self, start = None, boundingBoxes = None):
        self.start = start
        if(boundingBoxes != None):
            self.boundingBoxes = boundingBoxes

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)

    
class VideoOcrBoundingBoxSchema:
    text = ""
    language = ""
    score = None
    vertices = None
    def __init__(self, text = "", language = "", score = None, vertices = None):
        self.text = text
        self.language = language
        self.score = score
        self.vertices = vertices
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)


class VideoOcrBoundingBoxScoreSchema:
    type = ""
    value = None
    def __init__(self, type = "", value = None):
        self.type = type
        self.value = value
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)

    

class VideoOcrBoundingBoxVerticesSchema:
    xmin = 0
    ymin = 0
    xmax = 0
    ymax = 0
    def __init__(self, xmin = 0, ymin = 0, xmax = 0, ymax = 0):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)