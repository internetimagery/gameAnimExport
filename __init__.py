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

class Animation(object):
    """
    An animation entry
    """
    def __init__(s, override={}):
        s.data = dict({
            "name"  : "",
            "range" : sorted(s.frameRange()),
            "layers": s.animLayers()
        }, **override)
    def frameRange(s):
        return [
            int(cmds.playbackOptions(q=True, min=True)),
            int(cmds.playbackOptions(q=True, max=True))
        ]
    def animLayers(s):
        rootLayer = cmds.animLayer(q=True, r=True)
        if rootLayer:
            additional = {}
            def search(layer):
                children = cmds.animLayer(layer, q=True, c=True)
                if children:
                    for child in children:
                        additional[child] = {}
                        search(child)
            search(rootLayer)
            if additional:
                for layer in additional:
                    mute = cmds.animLayer(layer, q=True, m=True)
                    solo = cmds.animLayer(layer, q=True, s=True)
                    additional[layer] = {
                        "mute"  : mute,
                        "solo"  : solo
                    }
                return additional
        return {}

class AnimationGUI(object):
    def __init__(s, anim):
        """
        Modify animation window
        """
        winName = "Animation_Entry"
        if cmds.window(winName, ex=True):
            cmds.deleteUI(winName)
        window = cmds.window(winName, t="Animation", rtf=True)
        cmds.columnLayout(adj=True)
        cmds.text(l="Create / Edit an Animation.", al="left", h=30)
        cmds.separator()
        name = cmds.textFieldGrp(
            l="Name: ",
            adj=2,
            tcc=lambda x: s.valid(name, s.updateName(x)))
        frame = cmds.intFieldGrp(
            l="Frame Range: ",
            nf=2,
            v1=anim.data["range"][0],
            v2=anim.data["range"][1],
            cc= lambda x, y: s.valid(frame, s.updateRange(x,y))
        )
        cmds.text(l="Animation Layers", al="left", h=30)
        cmds.separator()
        cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2))
        def addLayer(layer):
            enable = True if layer in anim.data["layers"] else False
            cmds.rowLayout(nc=3, adj=3)
            cmds.iconTextCheckBox(
                i="Solo_OFF.png",
                si="Solo_ON.png",
                v=anim.data["layers"][layer]["solo"] if enable else True,
                en=enable,
                cc=lambda x: s.updateLayer(layer, "solo", x)
            )
            cmds.iconTextCheckBox(
                i="Mute_OFF.png",
                si="Mute_ON.png",
                v=anim.data["layers"][layer]["mute"] if enable else True,
                en=enable,
                cc=lambda x: s.updateLayer(layer, "mute", x)
            )
            cmds.text(
                l=layer,
                al="left",
                en=enable,
            )
            cmds.setParent("..")
        for layer in (anim.data["layers"].keys() + ["BaseAnimation"]):
            addLayer(layer)
        cmds.showWindow(window)
    def valid(s, element, ok):
        if ok:
            cmds.control(element, e=True, bgc=(0.3,1,0.3))
        else:
            cmds.control(element, e=True, bgc=(1,0.4,0.4))
    def updateName(s, text):
        text = text.strip()
        if text:
            anim.name = text
            return True
        return False
    def updateRange(s, mini, maxi):
        if mini < maxi:
            anim.data["range"] = [mini, maxi]
            return True
        return False
    def updateLayer(s, layer, attr, value):
        anim.data["layers"][layer][attr] = value


anim = Animation({"name": "Test animation"})
AnimationGUI(anim)
