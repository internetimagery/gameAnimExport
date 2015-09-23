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
            "layers": s.animLayers()
        }
    def frameRange(s):
        return [
            cmds.playbackOptions(q=True, min=True),
            cmds.playbackOptions(q=True, max=True)
        ]
    def animLayers(s):
        rootLayer = cmds.animLayer(q=True, r=True)
        if rootLayer:
            additional = []
            def search(layer):
                children = cmds.animLayer(layer, q=True, c=True)
                if children:
                    for child in children:
                        additional.append(child)
                        search(child)
            search(rootLayer)
            if additional:
                for layer in additional:
                    mute = cmds.animLayer(layer, q=True, m=True)
                    solo = cmds.animLayer(layer, q=True, s=True)
                    print mute, solo, layer

        return {}

AnimationCreate()
