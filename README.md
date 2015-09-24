# Game Animation Export Tool
A Small tool to assist in exporting animations for game engines from Maya.

Particuarly useful when you want to animate a sequence in Maya, and export pieces of it into different files for the game engine.

Includes support for animation modification via animation layers.

To install, either:

* drag the "install.mel" file into your Maya viewport
* or drag the entire folder containing "__init__.py" (named "gameAnimExport") into your maya scripts directory. Creating a shelf icon with the code:
```
import gameAnimExport as game
game.MainWindow()
```
