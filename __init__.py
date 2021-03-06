# Game Animation Export Tool
# Created by Jason Dixon : 24/09/15
# http://internetimagery.com

import re
import report
import os.path
import datetime
import webbrowser
import unicodedata
import collections
import maya.mel as mel
import maya.cmds as cmds
try:
    import cPickle as pickle
except ImportError:
    import pickle

class Node(object):
    """ Store Data in Object """
    def __init__(s, name):
        s.name = name
        s._data = {}
    @property
    def data(s):
        try:
            s._data = pickle.loads(str(cmds.getAttr("%s.notes" % s.name)))
        except (ValueError, pickle.UnpicklingError):
            s._data = {}
        return s._data
    def check(s):
        if not cmds.objExists(s.name):
            sel = cmds.ls(sl=True)
            s.name = cmds.group(n=s.name, em=True)
            cmds.select(sel, r=True)
        if not cmds.attributeQuery("notes", n=s.name, ex=True):
            cmds.addAttr(s.name, ln="notes", sn="nts", dt="string", s=True)
    def save(s):
        s.check()
        cmds.setAttr("%s.notes" % s.name, l=False) # unlock attribute
        cmds.setAttr("%s.notes" % s.name, pickle.dumps(s._data, 0), type="string", l=True)
STORE = Node("GameExportData")

def title(text):
    cmds.text(l=text, al="left", h=30)
    cmds.separator()

def textLimit(text, limit=100):
    return text if len(text) < limit else "%s ... %s" % (text[:limit-15], text[-10:])

def absolutePath(path):
    root = cmds.workspace(q=True, rd=True)
    return os.path.realpath(os.path.join(root, path))

def relativePath(path):
    root = cmds.workspace(q=True, rd=True)
    rPath = os.path.relpath(path, root)
    return absolutePath(path).replace("\\", "/") if rPath[:2] == ".." else rPath.replace("\\", "/")

# Loading data from old datatype for backwards compatibility
import json
def loadLegacy(dataName):
    try:
        return json.loads(cmds.fileInfo(dataName, q=True)[0].decode("unicode_escape"))
    except (ValueError, IndexError):
        return {}

def loadInfo(dataName):
    return STORE.data.get(dataName, {}) or loadLegacy(dataName)

def saveInfo(dataName, data):
    STORE.data[dataName] = data
    STORE.save()

def getAllLayers():
    rootLayer = cmds.animLayer(q=True, r=True)
    if rootLayer:
        def search(layer, depth=0):
            children = cmds.animLayer(layer, q=True, c=True)
            if children:
                for child in children:
                    layers[child] = {"depth" : depth}
                    search(child, depth+1)
        layers = collections.OrderedDict()
        search(rootLayer)
        if layers:
            for layer in layers:
                mute = cmds.animLayer(layer, q=True, m=True)
                solo = cmds.animLayer(layer, q=True, s=True)
                layers[layer]["mute"] = mute
                layers[layer]["solo"] = solo
            return layers
    return {}

def setLayers(solo=[], mute=[]): # include only layers that are on mute/solo
    # Prep our layers
    layers = getAllLayers()
    for layer in layers:
        options = layers[layer]
        if options["solo"]:
            cmds.animLayer(layer, e=True, s=False)
        if layers[layer]["mute"]:
            cmds.animLayer(layer, e=True, m=False)
    # Modify our layers
    if solo:
        for layer in solo:
            if cmds.animLayer(layer, q=True, ex=True):
                cmds.animLayer(layer, e=True, s=True)
    if mute:
        for layer in mute:
            if cmds.animLayer(layer, q=True, ex=True):
                cmds.animLayer(layer, e=True, m=True)

iconSize = 25 # Global icon size for all listings

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
        with report.Report():
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
                    l="|    " * s.layers[layer]["depth"] + layer if enable else layer,
                    al="left",
                    en=enable,
                )
                cmds.setParent("..")
            for layer in (reversed(["BaseAnimation"] + s.layers.keys())):
                addLayer(layer)
            cmds.showWindow(window)
    def valid(s, element, ok):
        if ok:
            cmds.control(element, e=True, bgc=(0.3,1,0.3))
        else:
            cmds.control(element, e=True, bgc=(1,0.4,0.4))
    @report.Report()
    def updateName(s, text):
        text = text.strip()
        if text:
            if s.validation(text): # Validate name
                s.anim.data["name"] = text.title()
                s.change()
                return True
        return False
    @report.Report()
    def updateRange(s, mini, maxi):
        if mini < maxi:
            s.anim.data["range"] = [mini, maxi]
            s.change()
            return True
        return False
    @report.Report()
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
        with report.Report():
            # Build window
            name = "GameAnimExportWindow"
            s.animationData = []
            if cmds.window(name, ex=True):
                cmds.deleteUI(name)
            s.window = cmds.window(name, t="Animations", rtf=True)
            s.wrapper = cmds.columnLayout(adj=True)
            s.buildSelector()
            cmds.showWindow(s.window)
            cmds.scriptJob(e=["PostSceneRead", s.buildSelector], p=s.window)
            cmds.scriptJob(e=["NewSceneOpened", s.buildSelector], p=s.window)
            cmds.scriptJob(e=["timeChanged", s.highlightAnimation], p=s.window)

    @report.Report()
    def buildSelector(s):
        s.animationData = []
        dataNameBase = "GameAnimExportData"
        index = 1
        characters = {}
        while True:
            dataName = dataNameBase + str(index)
            index += 1
            try:
                data = loadInfo(dataName)
                characters[dataName] = data["pref"]
            except:
                break
        s.clearElement(s.wrapper)
        cmds.setParent(s.wrapper)
        title("Select a character:")
        cmds.scrollLayout(cr=True, bgc=(0.2,0.2,0.2))
        def addChar(char):
            cmds.iconTextButton(
                st="iconAndTextHorizontal",
                i="ghostOff.png",
                l=characters[char],
                ann="Open the character: %s." % characters[char],
                h=50,
                c=lambda: s.buildCharacter(char)
                )
        if characters:
            for char in characters:
                addChar(char)
        else:
            cmds.text(l="There are no characters set for this scene.\nTime to create one. :)")
        cmds.setParent("..")
        cmds.button(
            l="Create New Character",
            ann="Create a new character.",
            c=lambda x: s.buildCharacter(dataName)
        )

    @report.Report()
    def buildCharacter(s, dataName):
        s.dataName = dataName
        s.dirty = False
        s.data = loadInfo(s.dataName)
        # Initialize Data
        s.data["pref"] = s.data.get("pref", "Default")
        s.data["objs"] = s.data.get("objs", [])
        s.data["dirs"] = s.data.get("dirs", [])
        s.animationData = []
        s.data["anim"] = s.data.get("anim", {})
        s.clearElement(s.wrapper)
        cmds.setParent(s.wrapper)
        cmds.button(
            l="<-- Return to character selection.",
            ann="Go back to the characer selection screen to pick a new character.",
            c=lambda x: s.buildSelector()
        )
        title("Animation Export Options:")
        prefix = cmds.textFieldGrp(
            l="Character Name: ",
            tx=s.data["pref"],
            adj=1,
            ann="Choose a name that represents the character, to prefix all animation exports.",
            tcc=lambda x:s.changePrefix(prefix, x)
        )
        cmds.iconTextButton(
            st="iconAndTextHorizontal",
            i="fluidCacheCreate.png",
            l="Add a new Animation.",
            fn="boldLabelFont",
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
            fn="boldLabelFont",
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
            i="menuIconFile.png", # fileOpen.png
            l="Add folder for exporting.",
            fn="boldLabelFont",
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
        s.highlightAnimation()
    @report.Report()
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
    @report.Report()
    def setAnimation(s, anim):
        cmds.playbackOptions(
            e=True,
            min=anim.data["range"][0],
            max=anim.data["range"][1]
        )
        setLayers(
            solo = anim.data["layers"]["solo"],
            mute = anim.data["layers"]["mute"]
        )
    def validateAnimName(s, name): # Validate anim name
        if re.match(r"^[\w\s]{2,80}$", name):
            if name.lower().replace(" ", "_") not in [a.data["name"].lower().replace(" ", "_") for a in s.animationData]:
                return True
        return False
    @report.Report()
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
    @report.Report()
    def removeAnimation(s, listElement, anim):
        if cmds.layout(listElement, ex=True):
            cmds.deleteUI(listElement)
        if anim in s.animationData:
            s.animationData.remove(anim)
            s.data["anim"] = s.extractAnimationData(s.animationData)
            s.save()
        print "Removing Animation:", anim.data["name"]
    @report.Report()
    def editAnimation(s, listElement, anim):
        def dataChanged():
            s.data["anim"] = s.extractAnimationData(s.animationData)
            s.save()
            s.displayAnimations(listElement, s.animationData)
        AnimationGUI(anim, s.validateAnimName, dataChanged)
    @report.Report()
    def displayAnimations(s, listElement, items):
        if items:
            s.clearElement(listElement)
            s.displayAnim = {} # Store reference to GUI frames
            def addAnim(item):
                row = cmds.rowLayout(
                    nc=6,
                    adj=2,
                    p=listElement)
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i="animCurveTA.svg",
                    h=iconSize,
                    w=iconSize
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
                    h=iconSize,
                    w=iconSize,
                    c=lambda: s.performExport(item)
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="traxFrameRange.png",
                    ann="Go to frame range %s - %s and set animaton layers." % (
                        item.data["range"][0],
                        item.data["range"][1]
                    ),
                    h=iconSize,
                    w=iconSize,
                    c=lambda: s.setAnimation(item)
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="setEdEditMode.png",
                    ann="Edit Animation",
                    h=iconSize,
                    w=iconSize,
                    c=lambda: s.editAnimation(listElement, item)
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="removeRenderable.png",
                    ann="Remove this animation.",
                    h=iconSize,
                    w=iconSize,
                    c=lambda: s.removeAnimation(row, item)
                )
                s.displayAnim[item] = row
            for item in sorted(items, key=lambda x: x.data["name"]):
                addAnim(item)
    @report.Report()
    def highlightAnimation(s):
        if s.animationData:
            frame = cmds.currentTime(q=True)
            layers = getAllLayers()
            mute = sorted([l for l in layers if layers[l]["mute"]])
            solo = sorted([l for l in layers if layers[l]["solo"]])
            if s.dirty:
                for row in [s.displayAnim[r] for r in s.displayAnim]:
                    if cmds.layout(row, ex=True):
                        cmds.layout(row, e=True, bgc=[0.2,0.2,0.2])
                        s.dirty = False
            for anim in s.animationData:
                l = anim.data["layers"]
                r = anim.data["range"]
                if sorted(l["mute"]) == mute and sorted(l["solo"]) == solo:
                    if r[0] < frame < r[1]:
                        row = s.displayAnim[anim]
                        if cmds.layout(row, ex=True):
                            cmds.layout(row, e=True, bgc=[0.25,0.25,0.25])
                            s.dirty = True
    @report.Report()
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
    @report.Report()
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
    @report.Report()
    def displayExportSelection(s, listElement, items):
        s.clearElement(listElement)
        if items:
            def addSel(item):
                exists = cmds.objExists(item)
                row = cmds.rowLayout(
                    nc=4,
                    adj=2,
                    bgc=(0.2,0.2,0.2) if exists else (1,0.4,0.4),
                    p=listElement)
                if exists and cmds.objectType(item) == "joint":
                    icon = "joint.svg"
                elif exists:
                    icon = "cube.png"
                else:
                    icon = "vacantCell.png"
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i=icon,
                    h=iconSize,
                    w=iconSize,
                )
                cmds.text(
                    l=textLimit(item),
                    al="left",
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="aselect.png",
                    ann="Select the object in the scene.",
                    en=exists,
                    h=iconSize,
                    w=iconSize,
                    c=lambda: cmds.select(item, r=True) if cmds.objExists(item) else None
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="removeRenderable.png",
                    ann="Remove this object from the export selection.",
                    h=iconSize,
                    w=iconSize,
                    c=lambda: s.removeExportSelection(row, item)
                )
            for item in items:
                addSel(item)
    @report.Report()
    def addExportFolder(s, listElement):
        folder = cmds.fileDialog2(ds=2, cap="Select a Folder.", fm=3, okc="Select Folder")
        if folder:
            folder = relativePath(folder[0])
            print folder
            if folder in s.data["dirs"]:
                cmds.confirmDialog(t="whoops", m="The folder you chose is already there.")
            else:
                print "Adding Export Folder:", folder
                s.data["dirs"].append(folder)
                s.save()
                s.displayExportFolders(listElement, s.data["dirs"])
    @report.Report()
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
    @report.Report()
    def displayExportFolders(s, listElement, items):
        s.clearElement(listElement)
        if items:
            def addRow(item):
                real = absolutePath(item)
                exists = os.path.isdir(real)
                if exists:
                    icon = "navButtonBrowse.png"
                else:
                    icon = "vacantCell.png"
                row = cmds.rowLayout(
                    nc=4,
                    adj=2,
                    h=30,
                    bgc=(0.2,0.2,0.2) if exists else (1,0.4,0.4),
                    p=listElement)
                cmds.iconTextStaticLabel(
                    st="iconOnly",
                    i=icon,
                    h=iconSize,
                    w=iconSize
                )
                cmds.text(
                    l=textLimit(item),
                    al="left",
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="traxOpenLibrary.png",
                    ann="Open the folder.",
                    en=exists,
                    h=iconSize,
                    w=iconSize,
                    c=lambda: webbrowser.open(real) if os.path.isdir(real) else None
                )
                cmds.iconTextButton(
                    st="iconOnly",
                    i="removeRenderable.png",
                    ann="Remove this folder from the export list.",
                    h=iconSize,
                    w=iconSize,
                    c=lambda: s.removeExportFolder(row, item)
                )
            for item in items:
                addRow(item)
    def performExport(s, anim, prebake=False):
        # Validate scene data before export
        if not s.data["pref"]:
            return cmds.confirmDialog(t="Oh no..", m="Please add a prefix.")
        pref = s.data["pref"]
        if not s.data["objs"]:
            return cmds.confirmDialog(t="Oh no..", m="Please add some objects to export.")
        objs = [o for o in s.data["objs"] if cmds.objExists(o)]
        if not objs:
            return cmds.confirmDialog(t="Oh no..", m="None of the selected objects could be found.")
        if not s.data["dirs"]:
            return cmds.confirmDialog(t="Oh no..", m="Please add at least one folder to export into.")
        dirs = [absolutePath(d) for d in s.data["dirs"]]
        dirs = [d for d in dirs if os.path.isdir(d)]
        if not dirs:
            return cmds.confirmDialog(t="Oh no..", m="None of the chosen folders could be found.")
        # Get our animation data
        data = anim.data
        if not data["name"] or not data["range"] or not data["layers"]:
            return cmds.configDialog(t="Oh no..", m="There was an issue with you anim data.")
        with cleanModify():
            print "Exporting %s." % data["name"]
            # Prep our animation
            s.setAnimation(anim)

            if prebake: # Bake out animation manually before export

                cmds.bakeResults(
                    objs,
                    simulation=True,
                    hierarchy="below",
                    t=tuple(anim.data["range"]),
                    sampleBy=1, # Mass keyframes, each frame!
                    disableImplicitControl=True,
                    # sparseAnimCurveBake=True,
                    removeBakedAttributeFromLayer=True,
                    # smart=(True, 5)
                    minimizeRotation=True
                )
                # Wall off edges of time
                cmds.setKeyframe(objs, i=True, t=anim.data["range"][0])
                cmds.setKeyframe(objs, i=True, t=anim.data["range"][1])
                # Remove Excess frames
                times = cmds.keyframe(objs, q=True, tc=True)
                frame_range = min(times), max(times)
                if frame_range[0] < anim.data["range"][0]:
                    cmds.cutKey(objs, t=(frame_range[0], anim.data["range"][0] - 0.1), cl=True)
                if frame_range[1] > anim.data["range"][1]:
                    cmds.cutKey(objs, t=(anim.data["range"][1] + 0.1, frame_range[1]), cl=True)


            # Create filename
            validate = r"[^\w_-]"
            filename = "%s@%s" % (
                re.sub(validate, "_", pref), # unicodedata.normalize("NFKD", pref)),
                re.sub(validate, "_", data["name"]) # unicodedata.normalize("NFKD", data["name"]))
                )
            files = [os.path.realpath(os.path.join(d, filename)) for d in dirs]
            # Prepare export command (yikes)
            command =  """
FBXResetExport; FBXExportInAscii -v true;
FBXExportCameras -v false; FBXExportLights -v false;
FBXExportUpAxis %(axis)s; FBXExportUseSceneName -v false;
FBXExportGenerateLog -v false; FBXExportConstraints -v false;
FBXExportAxisConversionMethod addFbxRoot;
FBXProperty "Export|IncludeGrp|Animation" -v true;
FBXExportBakeComplexAnimation -v true;
FBXExportBakeComplexStart -v %(start)s;
FBXExportBakeComplexEnd -v %(end)s;
FBXExportBakeComplexStep -v 1;
FBXExportBakeResampleAnimation -v true;
FBXExportApplyConstantKeyReducer -v true;
 /* FBXExportSkeleton -v true; */
FBXExportSkins -v true;
FBXExportShapes -v true;
FBXExportInputConnections -v false;
FBXExportEmbeddedTextures -v false;
""" % {
    "axis"  : cmds.upAxis(q=True, ax=True),
    "start" : data["range"][0],
    "end"   : data["range"][1]
    }
            for f in files:
                command += "FBXExport -f \"%s.fbx\" -s;\n" % f.replace("\\", "/")
            # Make our selection
            cmds.select(objs, r=True)
            # Run our mel command behemoth
            print "Running Mel:"
            for i, line in enumerate(command.split("\n")):
                if line:
                    print i, "\t", line
            mel.eval(command)
            # # Save out a convenience json file too
            # for f in files:
            #     with open(f + ".json", "w") as w:
            #         w.write(json.dumps({
            #             "start"     : data["range"][0],
            #             "end"       : data["range"][1],
            #             "modified"  : str(datetime.datetime.now())
            #         }))



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
