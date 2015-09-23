
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
    def __init__(s, anim, validation, changeCallback):
        """
        Modify animation window
        """
        s.anim = anim
        s.validation = validation # Name validation
        s.change = changeCallback
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
            enable = True if layer in s.anim.data["layers"] else False
            cmds.rowLayout(nc=3, adj=3)
            cmds.iconTextCheckBox(
                i="Solo_OFF.png",
                si="Solo_ON.png",
                v=s.anim.data["layers"][layer]["solo"] if enable else True,
                en=enable,
                cc=lambda x: s.updateLayer(layer, "solo", x)
            )
            cmds.iconTextCheckBox(
                i="Mute_OFF.png",
                si="Mute_ON.png",
                v=s.anim.data["layers"][layer]["mute"] if enable else True,
                en=enable,
                cc=lambda x: s.updateLayer(layer, "mute", x)
            )
            cmds.text(
                l=layer,
                al="left",
                en=enable,
            )
            cmds.setParent("..")
        for layer in (s.anim.data["layers"].keys() + ["BaseAnimation"]):
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
        s.anim.data["layers"][layer][attr] = value
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
            tcc=lambda x:s.changePrefix(prefix, x)
        )
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="animateSweep.png",
            l="Add a new Animation.",
            c=lambda: s.addAnimation(animWrapper)
            )
        animWrapper = cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2))
        cmds.setParent("..")
        cmds.button(
            l="Export All",
            c=s.performExport
        )
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="selectByObject.png",
            l="Add selected objects to export.",
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
            c=lambda: s.addExportFolder(dirWrapper)
            )
        dirWrapper = cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2), h=80)
        cmds.setParent("..")
        cmds.button(
            l="Clear All",
            c=lambda x: s.clearExportFolders(dirWrapper)
        )
        # Display Data data
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
        else:
            cmds.control(element, e=True, bgc=(1,0.4,0.4))
    def addAnimation(s, listElement):
        def validateAnimName(name): # Validate anim name
            if name and 1 < len(name) < 30 and name not in [a.data["name"] for a in s.animationData]:
                return True
            return False
        def dataChanged():
            print anim.data
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
        AnimationGUI(anim, validateAnimName, dataChanged)
        s.displayAnimations(listElement, s.animationData)
    def removeAnimation(s, listElement, anim):
        if cmds.layout(listElement, ex=True):
            cmds.deleteUI(listElement)
        if anim in s.animationData:
            s.animationData.remove(anim)
        print "Removing Animation:", anim.data["name"]
    def displayAnimations(s, listElement, items):
        if items:
            s.clearElement(listElement)
            def addAnim(item):
                row = cmds.rowLayout(
                    nc=3,
                    adj=2,
                    p=listElement)
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i="cube.png",
                    h=20,
                    w=20,
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
                    i="removeRenderable.png",
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
                    c=lambda: s.removeExportFolder(row, item)
                )
            for item in items:
                addRow(item)
    def performExport(s, *args):
        print s.data
        print "exporting anims"

MainWindow()
