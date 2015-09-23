# TODO

# Save scene information json into fileInfo
# toolbox for viewing information
# seperate window for adding information
# store animation layer information, turned on or off, per anim
# store frame information per animaton
# store rig information (only once?)

import maya.cmds as cmds
from json import loads, dumps

class Store(object):
    """
    Store metadata
    """
    def __init__(s):
        s.dataName = "GameAnimExport"
        try:
            s.data = loads(cmds.fileInfo(s.dataName, q=True)[0].decode("unicode_escape"))
        except ValueError, IndexError:
            s.data = {}
    def get(s, k, default=None):
        return s.data.get(k, default)
    def set(s, k, v):
        s.data[k] = v
        cmds.fileInfo(k, dumps(s.data))

class AnimationCreate(object):
    """
    Window to create or edit an animation entry
    """
    def __init__(s, override={}):
        s.data = {
            "range" : s.frameRange(),
            "layers": {}
        }
    def frameRange(s):
        return [
            cmds.playbackOptions(q=True, min=True),
            cmds.playbackOptions(q=True, max=True)
        ]
