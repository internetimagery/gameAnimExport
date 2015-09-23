
# Save scene information json into fileInfo
# toolbox for viewing information
# seperate window for adding information
# store animation layer information, turned on or off, per anim
# store frame information per animaton
# store rig information (only once?)

import maya.cmds as cmds
from json import loads, dumps

def title(text):
    cmds.text(l=text, al="left", h=30)
    cmds.separator()

def loadInfo(dataName):
    try:
        return loads(cmds.fileInfo(dataName, q=True)[0].decode("unicode_escape"))
    except (ValueError, IndexError):
        return {}

def saveInfo(dataName, data):
    cmds.fileInfo(dataName, dumps(data))

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
    def __init__(s, anim, validation=[], dirty=None):
        """
        Modify animation window
        """
        s.validation = validation
        s.dirty = dirty
        winName = "Animation_Entry"
        if cmds.window(winName, ex=True):
            cmds.deleteUI(winName)
        window = cmds.window(winName, t="Animation", rtf=True)
        cmds.columnLayout(adj=True)
        title("Create / Edit an Animation.")
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
        title("Animation Layers")
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
            if s.validation: # Validate name
                for validate in s.validation:
                    if not validate(text):
                        return False
            anim.name = text
            if s.dirty: # Mark changes as having been made
                s.dirty()
            return True
        return False
    def updateRange(s, mini, maxi):
        if mini < maxi:
            anim.data["range"] = [mini, maxi]
            if s.dirty: # Mark changes as having been made
                s.dirty()
            return True
        return False
    def updateLayer(s, layer, attr, value):
        anim.data["layers"][layer][attr] = value
        if s.dirty: # Mark changes as having been made
            s.dirty()

class MainWindow(object):
    """
    Display animations
    """
    def __init__(s):
        s.dataName = "GameAnimExportData"
        s.data = loadInfo(s.dataName)
        # Initialize Data
        s.data["objs"] = s.data.get("objs", [])
        name = "GameAnimExportWindow"
        if cmds.window(name, ex=True):
            cmds.deleteUI(name)
        s.window = cmds.window(name, t="Animations", rtf=True)
        cmds.columnLayout(adj=True)
        title("Export Options:")
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="animateSweep.png",
            l="Add a new Animation.",
            c=lambda: s.addAnimation(animWrapper)
            )
        animWrapper = cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2))
        cmds.setParent("..")
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="selectByObject.png",
            l="Use selected objects for export.",
            c=lambda: s.setExportSelection(selWrapper, cmds.ls(sl=True))
            )
        selWrapper = cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2), h=80)
        cmds.setParent("..")
        s.saveBtn = cmds.button(
            l="SAVE",
            h=40,
            c=s.saveData
        )
        # Initialize data
        s.dirty(True)
        s.displayExportSelection(selWrapper, s.data["objs"])
        cmds.showWindow(s.window)
    def setExportSelection(s, listElement, items):
        s.data["objs"] = items
        s.dirty()
        s.displayExportSelection(listElement, items)
    def displayExportSelection(s, listElement, items):
        existing = cmds.layout(listElement, q=True, ca=True)
        if existing:
            cmds.deleteUI(existing)
        if items:
            for item in items:
                cmds.rowLayout(
                    nc=2,
                    adj=2,
                    bgc=(0.2,0.2,0.2) if cmds.objExists(item) else (1,0.4,0.4),
                    p=listElement)
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i="joint.svg" if cmds.objectType(item) == "joint" else "cube.png",
                    h=25,
                    w=25,
                    l=item
                )
                cmds.text(
                    l=item,
                    al="left",
                )
    def addAnimation(s, listElement):
        print "add new animation"

    def dirty(s, clean=False):
        titleName = cmds.window(s.window, q=True, t=True)
        if clean:
            cmds.button(s.saveBtn, e=True, bgc=(0.5,0.5,0.5), en=False)
            cmds.window(s.window, e=True, t=titleName.replace("*", ""))
        else:
            cmds.button(s.saveBtn, e=True, bgc=(0.3,1,0.3), en=True)
            if titleName[-1:] != "*":
                cmds.window(s.window, e=True, t=titleName+"*")
    def saveData(s, *args):
        print "Saving"
        s.dirty(True)
MainWindow()
