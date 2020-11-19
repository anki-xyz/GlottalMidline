"""
Load images and annotate the A and P point

Written by Andreas Kist and modified by Julian Zilker
"""

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QGridLayout, QWidget, QSlider, QLabel, QCheckBox, QSizePolicy
from PyQt5.QtCore import pyqtSignal, Qt
import pyqtgraph as pg
import imageio as io
import numpy as np
import json
import os
from glob import glob

from PyQt5.QtCore import pyqtRemoveInputHook
from pdb import set_trace


def trace():
    pyqtRemoveInputHook()
    set_trace()


class ROI:
    def __init__(self, pos=[100, 100], shown=True):
        """
        ROI class that keeps ROI position and if it is active.

        :param pos: list, tuple or pyqtgraph Point
        :param shown: boolean
        """
        self.pos = pos
        self.shown = shown

    def serialize(self):
        """
        Serializes object to dictionary
        :return: dict
        """
        return {'pos': tuple(self.pos), 'shown': self.shown}

class ImageView(pg.ImageView):
    keysignal = pyqtSignal(int)
    mousesignal = pyqtSignal(int)

    def __init__(self, im, rois=None, parent=None):
        """
        Custom ImageView class to handle ROIs dynamically

        :param im: The image to be shown
        :param rois: The rois for this image
        :param parent: The parent widget where the window is embedded
        """
        # Set Widget as parent to show ImageView in Widget
        super().__init__(parent=parent)

        # Set 2D image
        self.setImage(im)
        self.rois = rois
        self.realRois = []
        self.colors = ['1a87f4', 'ebf441', '9b1a9b', '42f489']
        self.getView().setMenuEnabled(False)

        self.updateROIs()

        # Set reference to stack
        self.stack = parent


    def mousePressEvent(self, e):
        # Important, map xy coordinates to scene!
        xy = self.getImageItem().mapFromScene(e.pos())

        # Set posterior point
        if e.button() == Qt.LeftButton:
            self.realRois[0].setPos(xy)
            self.rois[0].shown = True
            # Check checkbox
            self.mousesignal.emit(0)

        # Set anterior point
        if e.button() == Qt.RightButton:
            self.realRois[1].setPos(xy)
            self.rois[0].shown = True
            # Check checkbox
            self.mousesignal.emit(1)

        # MiddleButton for +1
        if e.button() == Qt.MiddleButton:
            self.stack.z.setValue(self.stack.curId + 1)

    def updateROIs(self):
        """
        Cleans current ROIs from scene and creates the ROIs for the current image.

        :return:
        """
        # Remove all ROIs on scene
        for i in self.realRois:
            self.getView().removeItem(i)

        self.realRois = []

        # Iterate across ROIs
        if self.rois is not None:
            i = 0
            ### Create ROIs with different colors ###
            for r in self.rois:
                t = pg.CrosshairROI(r.pos)
                t.setPen(pg.mkPen(self.colors[i]))
                t.aspectLocked = True
                t.rotateAllowed = False
                ### Storing, not actually saving! ###
                t.sigRegionChanged.connect(self.saveROIs)
                self.realRois.append(t)

                if r.shown:
                    self.getView().addItem(self.realRois[-1])

                i += 1

    def saveROIs(self):
        """
        Saves the ROIs positions
        :return:
        """
        for i in range(len(self.realRois)):
            self.rois[i].pos = self.realRois[i].pos()

    def getROIs(self):
        """Saves and returns the current ROIs"""
        self.saveROIs()

        return self.rois

    def keyPressEvent(self, ev):
        """Pass keyPressEvent to parent classes
        
        Parameters
        ----------
        ev : event
            key event
        """
        self.keysignal.emit(ev.key())


class Stack(QWidget):
    def __init__(self, files, rois=None):
        """
        Main Widget to keep track of the stack (or movie) and the ROIs.

        :param stack: ndarray
        :param rois: None or list of saved ROIs (json)
        """
        super().__init__()

        self.files = files
        self.colors = ['1a87f4', 'c17511', '9b1a9b', '0c7232']

        self.rois = self.createROIs(rois)

        self.curId = 0
        self.freeze = False

        im = io.imread(self.files[0])
        im = np.transpose(im, (1,0,2)) # Transpose for pyqtgraph ImageView

        self.dim = im.shape
        self.w = ImageView(im, rois=self.rois[0], parent=self)

        ### Create Grid Layout and add the main image window to layout ###
        self.l = QGridLayout()
        self.l.addWidget(self.w, 0, 0, 7, 1)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.w.setSizePolicy(sizePolicy)
        self.w.show()

        ### Slider for z (or time) ###
        self.z = QSlider(orientation=Qt.Horizontal)
        self.z.setMinimum(0)
        self.z.setMaximum(len(self.files)-1)
        self.z.setValue(0)
        self.z.setSingleStep(1)
        self.z.valueChanged.connect(self.changeZ)
        self.w.keysignal.connect(self.keyPress)
        self.w.mousesignal.connect(self.mousePress)

        ### Checkboxes for point selection ###
        self.p1 = QCheckBox("show/select")
        self.p1.setStyleSheet("color: #{}".format(self.colors[0]))
        self.p1.stateChanged.connect(self.checkROIs)
        self.p2 = QCheckBox("show/select")
        self.p2.setStyleSheet("color: #{}".format(self.colors[1]))
        self.p2.stateChanged.connect(self.checkROIs)

        ### Add checkboxes and labels to GUI ###
        self.l.addWidget(QLabel("Posterior point"), 0, 1)
        self.l.addWidget(self.p1, 1, 1)
        self.l.addWidget(QLabel("Anterior point"), 2, 1)
        self.l.addWidget(self.p2, 3, 1)

        ### Add another empty label to ensure nice GUI formatting ###
        self.ll = QLabel()
        self.ll.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
        self.l.addWidget(self.ll, 6, 1)

        ### Add z slider to GUI ###
        self.l.addWidget(QLabel("z position"), 7, 0, 1, 2)
        self.l.addWidget(self.z, 8, 0, 1, 2)

        self.setLayout(self.l)

        ### Update once the checkboxes and the ROIs ###
        self.updateCheckboxes()
        self.checkROIs()

    def createROIs(self, rois=None):
        tmp_rois = [[ROI([100 + i * 25, 100 + i * 25], False) for i in range(2)]
                for _ in range(len(self.files))]

        # Loads saved ROIs
        if type(rois) == list:
            for r in rois:
                tmp_rois[r['z']][r['id']].pos = r['pos']
                tmp_rois[r['z']][r['id']].shown = True

        return tmp_rois

    def updateCheckboxes(self):
        self.freeze = True
        self.p1.setChecked(self.rois[self.curId][0].shown)
        self.p2.setChecked(self.rois[self.curId][1].shown)
        self.freeze = False

    def checkROIs(self):
        # Save only when in "non-freeze" mode,
        #  meaning if I change z, and thus the checkboxes,
        #  do NOT save the current checkboxes, as it makes no sense.
        if not self.freeze:
            self.rois[self.curId][0].shown = self.p1.isChecked()
            self.rois[self.curId][1].shown = self.p2.isChecked()

            self.w.rois = self.rois[self.curId]
            self.w.updateROIs()

    def mousePress(self, roi_id):
        if roi_id == 0:
            self.p1.setChecked(True)

        elif roi_id == 1:
            self.p2.setChecked(True)

    def changeZ(self):
        # Save current view state (zoom, position, ...)
        viewBoxState = self.w.getView().getState()

        # Save current levels
        levels = self.w.getImageItem().levels

        # Save ROIs
        self.rois[self.curId] = self.w.getROIs()

        # New image position
        self.curId = self.z.value()
        self.updateCheckboxes()

        im = io.imread(self.files[self.curId])
        im = np.transpose(im, (1,0,2))
        self.dim = im.shape

        # Set current image and current ROI data
        self.w.setImage(im)
        self.w.rois = self.rois[self.curId]

        # Clear old ROIs and set new ROIs to scene
        self.w.updateROIs()

        # Get old zoom and set the new zoom level the same,
        #  repeat with the levels of previous z.
        self.w.getView().setState(viewBoxState)
        self.w.getImageItem().setLevels(levels)

    def keyPress(self, key):
        # AD for -1 +1
        if key == Qt.Key_D:
             self.z.setValue(self.curId + 1)

        elif key == Qt.Key_A:
            self.z.setValue(self.curId - 1)

        elif key == Qt.Key_1:
            self.p1.setChecked(not self.p1.isChecked())

        elif key == Qt.Key_2:
            self.p2.setChecked(not self.p2.isChecked())

        elif key == Qt.Key_Q:
            self.p1.setChecked(True)
            self.p2.setChecked(True)

    def keyPressEvent(self, e):
        # Emit Save command to parent class
        if e.key() == Qt.Key_S:
            self.w.keysignal.emit(e.key())


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_fn = None
        self.status = self.statusBar()
        self.menu = self.menuBar()

        self.file = self.menu.addMenu("&File")
        self.file.addAction("Open", self.open)
        self.file.addAction("Save", self.save)

        self.folder = None
        self.history = []

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle("AP Annotator")

    def connectROIs(self):
        for i in range(len(self.stack.w.realRois)):
            self.stack.w.realRois[i].sigRegionChanged.connect(self.p)

    def updateStatus(self):
        """Shows the current "z-value", i.e. the image ID, and its dimensions
        """
        self.status.showMessage('z: {} x: {} y: {}'.format(self.stack.z.value(),
                                                           self.stack.dim[0],
                                                           self.stack.dim[1]))

        self.connectROIs()

    def open(self):
        with open('settings.json', 'r') as file:
            keys_2_settings = json.load(file)

        folder = QFileDialog.getExistingDirectory(directory=keys_2_settings["default_directory"])
        print(folder)

        self.status.showMessage(folder)

        if folder:
            self.folder = folder
            self.fn_rois = os.path.join(folder, "ap.points")

            files_cache = glob(os.path.join(folder, "*.png"))

            # Distinguish files
            files = [i for i in files_cache if "seg" not in i]
            seg_files = [i for i in files_cache if "seg" in i]

            # Sort all available files
            self.files = sorted(files, key=lambda path: int(path.split(os.sep)[-1][:-4]))
            self.seg_files = sorted(seg_files, key=lambda path: int(path.split(os.sep)[-1][:-8]))

            # Check correct sorting
            for index, file_path in enumerate(self.files):
                file_name = file_path.split(os.sep)[-1][:-4]
                if int(file_name) != index:
                    raise AssertionError("Something went wrong when assigning and ID to an image name")

            for index, file_path in enumerate(self.seg_files):
                file_name = file_path.split(os.sep)[-1][:-8]
                if int(file_name) != index:
                    raise AssertionError("Something went wrong when assigning and ID to an segmented image name")

            # If ROI file is existing, read and decode
            if os.path.isfile(self.fn_rois):
                with open(self.fn_rois, 'r') as fp:
                    rois = json.load(fp)['rois']

            else:
                rois = None

            # Create new Image pane and show first image,
            # connect slider and save function
            self.stack = Stack(self.files, rois=rois)
            self.setCentralWidget(self.stack)
            self.stack.z.valueChanged.connect(self.updateStatus)
            self.stack.w.keysignal.connect(self.savekeyboard)

            self.setWindowTitle("AP Annotator | Working on folder {}".format(self.folder))

    def p(self, e):
        """Shows current position
        
        Parameters
        ----------
        e : event
            Mouse event carrying the position
        """
        self.status.showMessage("{}".format(e.pos()))

    def save(self):
        """Saves all ROIs to file
        """
        if self.fn_rois:
            with open(self.fn_rois, "w") as fp:
                json.dump({
                    "rois": [{'z': i,
                              'id': j,
                              'pos': self.stack.rois[i][j].serialize()['pos']}
                             for i in range(len(self.stack.rois))
                             for j in range(len(self.stack.rois[i]))
                             if self.stack.rois[i][j].shown]
                }, fp, indent=4)

            self.status.showMessage("ROIs saved to {}".format(self.fn_rois), 1000)

    def savekeyboard(self, key):
        modifiers = QApplication.keyboardModifiers()

        if key == Qt.Key_S and modifiers == Qt.ControlModifier:
            self.save()



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    m = Main()
    m.show()

    sys.exit(app.exec_())
