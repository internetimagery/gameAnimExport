
# Save scene information json into fileInfo
# toolbox for viewing information
# seperate window for adding information
# store animation layer information, turned on or off, per anim
# store frame information per animaton
# store rig information (only once?)

import maya.cmds as cmds
from json import loads, dumps
from os.path import isdir, join, dirname, basename, realpath, relpath

def title(text):
    cmds.text(l=text, al="left", h=30)
    cmds.separator()

def textLimit(text, limit=100):
    return text if len(text) < limit else "%s ... %s" % (text[:limit-15], text[-10:])

def absolutePath(path):
    root = cmds.workspace(q=True, rd=True)
    return join(root, path)

def relativePath(path):
    root = cmds.workspace(q=True, rd=True)
    rPath = relpath(path, root)
    return absolutePath(path) if rPath[:2] == ".." else rPath

def loadInfo(dataName):
    try:
        return loads(cmds.fileInfo(dataName, q=True)[0].decode("unicode_escape"))
    except (ValueError, IndexError):
        return {}

def saveInfo(dataName, data):
    cmds.fileInfo(dataName, dumps(data))

def getAllLayers():
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
        result = {
            "solo"  : [],
            "mute"  : []
        }
        layers = getAllLayers()
        for layer in layers:
            if layers[layer]["solo"]:
                result["solo"].append(layer)
            if layers[layer]["mute"]:
                result["mute"].append(layer)
        return result

class AnimationGUI(object):
    def __init__(s, anim, validation, changeCallback):
        """
        Modify animation window
        """
        s.anim = anim
        s.validation = validation # Name validation
        s.change = changeCallback
        s.layers = getAllLayers() # Grab up to date layer info
        winName = "Animation_Entry"
        if cmds.window(winName, ex=True):
            cmds.deleteUI(winName)
        window = cmds.window(winName, t="Animation", rtf=True)
        cmds.columnLayout(adj=True)
        title("Create / Edit an Animation:")
        name = cmds.textFieldGrp(
            l="Name: ",
            tx=s.anim.data["name"],
            adj=2,
            tcc=lambda x: s.valid(name, s.updateName(x)))
        frame = cmds.intFieldGrp(
            l="Frame Range: ",
            nf=2,
            v1=s.anim.data["range"][0],
            v2=s.anim.data["range"][1],
            cc= lambda x, y: s.valid(frame, s.updateRange(x,y))
        )
        title("Animation Layers")
        cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2))
        def addLayer(layer):
            enable = False if layer == "BaseAnimation" else True
            cmds.rowLayout(nc=3, adj=3)
            cmds.iconTextCheckBox(
                i="Solo_OFF.png",
                si="Solo_ON.png",
                v=True if enable and layer in s.anim.data["layers"]["solo"] else False,
                en=enable,
                cc=lambda x: s.updateLayer(layer, "solo", x)
            )
            cmds.iconTextCheckBox(
                i="Mute_OFF.png",
                si="Mute_ON.png",
                v=True if enable and layer in s.anim.data["layers"]["mute"] else False,
                en=enable,
                cc=lambda x: s.updateLayer(layer, "mute", x)
            )
            cmds.text(
                l=layer,
                al="left",
                en=enable,
            )
            cmds.setParent("..")
        for layer in (s.layers.keys() + ["BaseAnimation"]):
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
            if s.validation(text): # Validate name
                s.anim.data["name"] = text.title()
                s.change()
                return True
        return False
    def updateRange(s, mini, maxi):
        if mini < maxi:
            s.anim.data["range"] = [mini, maxi]
            s.change()
            return True
        return False
    def updateLayer(s, layer, attr, value):
        if value:
            s.anim.data["layers"][attr].append(layer)
        else:
            s.anim.data["layers"][attr].remove(layer)
        s.change()

class MainWindow(object):
    """
    Display animations
    """
    def __init__(s):
        s.dataName = "GameAnimExportData"
        s.data = loadInfo(s.dataName)
        # Initialize Data
        s.data["pref"] = s.data.get("pref", "Default")
        s.data["objs"] = s.data.get("objs", [])
        s.data["dirs"] = s.data.get("dirs", [])
        s.animationData = []
        s.data["anim"] = s.data.get("anim", {})
        # Build window
        name = "GameAnimExportWindow"
        if cmds.window(name, ex=True):
            cmds.deleteUI(name)
        s.window = cmds.window(name, t="Animations", rtf=True)
        cmds.columnLayout(adj=True)
        title("Animation Export Options:")
        prefix = cmds.textFieldGrp(
            l="Animation Prefix: ",
            tx=s.data["pref"],
            adj=1,
            ann="Choose a name to prefix all animation exports.",
            tcc=lambda x:s.changePrefix(prefix, x)
        )
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="animateSweep.png",
            l="Add a new Animation.",
            ann="Create a new animation listing.",
            c=lambda: s.addAnimation(animWrapper)
            )
        animWrapper = cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2))
        cmds.setParent("..")
        cmds.button(
            l="Export All",
            c=lambda x: [s.performExport(a) for a in s.animationData]
        )
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="selectByObject.png",
            l="Add selected objects to export.",
            ann="Select some objects (typically the rig) and press the button to add them.",
            c=lambda: s.addExportSelection(selWrapper, cmds.ls(sl=True))
            )
        selWrapper = cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2), h=80)
        cmds.setParent("..")
        cmds.button(
            l="Clear All",
            c=lambda x: s.clearExportSelection(selWrapper)
        )
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="menuIconFile.png",
            l="Add folder for exporting.",
            ann="Pick some folders to export animations into. Folders that don't exist will be skipped.",
            c=lambda: s.addExportFolder(dirWrapper)
            )
        dirWrapper = cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2), h=80)
        cmds.setParent("..")
        cmds.button(
            l="Clear All",
            c=lambda x: s.clearExportFolders(dirWrapper)
        )
        # Display Data data
        if s.data["anim"]:
            for anim in s.data["anim"]:
                s.animationData.append(Animation(anim))
        s.displayAnimations(animWrapper, s.animationData    )
        s.displayExportSelection(selWrapper, s.data["objs"])
        s.displayExportFolders(dirWrapper, s.data["dirs"])
        cmds.showWindow(s.window)
    def save(s):
        saveInfo(s.dataName, s.data)
    def clearElement(s, element):
        existing = cmds.layout(element, q=True, ca=True)
        if existing:
            for layout in existing:
                try:
                    cmds.deleteUI(existing)
                except RuntimeError:
                    pass
    def changePrefix(s, element, text):
        text = text.strip().title()
        if text and 2 < len(text) < 30 and "@" not in text:
            cmds.layout(element, e=True, bgc=(0.3,1,0.3))
            s.data["pref"] = text
            s.save()
        else:
            cmds.control(element, e=True, bgc=(1,0.4,0.4))
    def extractAnimationData(s, anims):
        return sorted([a.data for a in anims], key=lambda x: x["range"][0])
    def validateAnimName(name): # Validate anim name
        if name and 1 < len(name) < 30 and name not in [a.data["name"] for a in s.animationData]:
            return True
        return False
    def addAnimation(s, listElement):
        def dataChanged():
            s.data["anim"] = s.extractAnimationData(s.animationData)
            s.save()
            s.displayAnimations(listElement, s.animationData)
        basename = "Anim_"
        index = 1
        animName = basename + str(index)
        while animName in [a.data["name"] for a in s.animationData]:
            index += 1
            animName = basename + str(index)
        anim = Animation({
            "name"  : animName
            })
        s.animationData.append(anim)
        s.data["anim"] = s.extractAnimationData(s.animationData)
        s.save()
        AnimationGUI(anim, s.validateAnimName, dataChanged)
        s.displayAnimations(listElement, s.animationData)
    def removeAnimation(s, listElement, anim):
        if cmds.layout(listElement, ex=True):
            cmds.deleteUI(listElement)
        if anim in s.animationData:
            s.animationData.remove(anim)
            s.data["anim"] = s.extractAnimationData(s.animationData)
            s.save()
        print "Removing Animation:", anim.data["name"]
    def editAnimation(s, listElement, anim):
        def dataChanged():
            s.data["anim"] = s.extractAnimationData(s.animationData)
            s.save()
            s.displayAnimations(listElement, s.animationData)
        AnimationGUI(anim, s.validateAnimName, dataChanged)
    def displayAnimations(s, listElement, items):
        if items:
            s.clearElement(listElement)
            def addAnim(item):
                row = cmds.rowLayout(
                    nc=5,
                    adj=2,
                    p=listElement)
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i="animCurveTA.svg",
                    h=25,
                    w=25
                )
                cmds.text(
                    l="%s - %s : %s" % (
                        item.data["range"][0],
                        item.data["range"][1],
                        textLimit(item.data["name"])
                        ),
                    al="left",
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="render.png",
                    ann="Export Animation",
                    h=25,
                    w=25,
                    c=lambda: s.performExport(item)
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="editBookmark.png",
                    ann="Edit Animation",
                    h=25,
                    w=25,
                    c=lambda: s.editAnimation(listElement, item)
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="removeRenderable.png",
                    ann="Remove this animation.",
                    h=25,
                    w=25,
                    c=lambda: s.removeAnimation(row, item)
                )
            for item in items:
                addAnim(item)
    def addExportSelection(s, listElement, items):
        if items:
            for item in items:
                if item not in s.data["objs"]:
                    print "Adding object:", item
                    s.data["objs"].append(item)
            s.save()
            s.displayExportSelection(listElement, s.data["objs"])
        else:
            cmds.confirmDialog(t="Oh no!", m="You need to select something.")
    def removeExportSelection(s, listElement, item):
        if cmds.layout(listElement, ex=True):
            cmds.deleteUI(listElement)
        if item in s.data["objs"]:
            s.data["objs"].remove(item)
            s.save()
        print "Removing Export Object:", item
    def clearExportSelection(s, listElement):
        s.data["objs"] = []
        s.save()
        print "Cleared Export Selection"
        s.displayExportSelection(listElement, [])
    def displayExportSelection(s, listElement, items):
        s.clearElement(listElement)
        if items:
            def addSel(item):
                exists = cmds.objExists(item)
                row = cmds.rowLayout(
                    nc=3,
                    adj=2,
                    bgc=(0.2,0.2,0.2) if exists else (1,0.4,0.4),
                    p=listElement)
                if exists and cmds.objectType(item) == "joint":
                    icon = "joint.svg"
                elif exists:
                    icon = "cube.png"
                else:
                    icon = "menuIconConstraints.png"
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i=icon,
                    h=20,
                    w=20,
                )
                cmds.text(
                    l=textLimit(item),
                    al="left",
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="removeRenderable.png",
                    ann="Remove this object from the export selection.",
                    c=lambda: s.removeExportSelection(row, item)
                )
            for item in items:
                addSel(item)
    def addExportFolder(s, listElement):
        folder = cmds.fileDialog2(ds=2, cap="Select a Folder.", fm=3, okc="Select Folder")
        if folder:
            folder = relativePath(folder[0])
            if folder in s.data["dirs"]:
                cmds.confirmDialog(t="whoops", m="The folder you chose is already there.")
            else:
                print "Adding Export Folder:", folder
                s.data["dirs"].append(folder)
                s.save()
                s.displayExportFolders(listElement, s.data["dirs"])
    def removeExportFolder(s, listElement, path):
        if cmds.layout(listElement, ex=True):
            cmds.deleteUI(listElement)
        if path in s.data["dirs"]:
            s.data["dirs"].remove(path)
            s.save()
        print "Removing Export Folder:", path
    def clearExportFolders(s, listElement):
        s.data["dirs"] = []
        s.save()
        print "Cleared Export Folders"
        s.displayExportFolders(listElement, [])
    def displayExportFolders(s, listElement, items):
        s.clearElement(listElement)
        if items:
            def addRow(item):
                row = cmds.rowLayout(
                    nc=3,
                    adj=2,
                    h=30,
                    bgc=(0.2,0.2,0.2) if isdir(absolutePath(item)) else (1,0.4,0.4),
                    p=listElement)
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i="outArrow.png",
                )
                cmds.text(
                    l=textLimit(item),
                    al="left",
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="removeRenderable.png",
                    ann="Remove this folder from the export list.",
                    c=lambda: s.removeExportFolder(row, item)
                )
            for item in items:
                addRow(item)
    def performExport(s, anim):
        # Validate animation data before export
        if not s.data["pref"]:
            return cmds.confirmDialog(t="Oh no..", m="Please add a prefix.")
        if not s.data["objs"]:
            return cmds.confirmDialog(t="Oh no..", m="Please add some objects to export.")
        if not s.data["dirs"]:
            return cmds.confirmDialog(t="Oh no..", m="Please add at least one folder to export into.")
        # Get our animation data
        data = s.extractAnimationData([anim])[0]
        with cleanModify():
            # Prep our layers
            if data["layers"]:
                for layer in data["layers"]:
                    options = data["layers"][layer]
                    print layer, options

        print "exporting anims"

class cleanModify(object):
    """
    Cleanly modify scene without permanent changes
    """
    def __enter__(s):
        s.selection = cmds.ls(sl=True)
        cmds.undoInfo(ock=True)

    def __exit__(s, *args):
        cmds.select(s.selection, r=True)
        cmds.undoInfo(cck=True)
        cmds.undo()

MainWindow()
