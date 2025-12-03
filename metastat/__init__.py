# SPDX-License-Identifier: GPL-3.0-or-later

import json

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
from eddy.core.commands.iri import CommandIRIAddAnnotationAssertion
from eddy.core.commands.nodes import CommandNodeAdd
from eddy.core.datatypes.graphol import Item
from eddy.core.datatypes.misc import DiagramMode
from eddy.core.diagram import Diagram
from eddy.core.functions.misc import snap
from eddy.core.functions.signals import connect, disconnect
from eddy.core.output import getLogger
from eddy.core.owl import (
    AnnotationAssertion,
    AnnotationAssertionProperty,
    IRI,
    Literal,
)
from eddy.core.plugin import AbstractPlugin
from eddy.ui.dock import DockWidget

from .model import (
    LiteralValue,
    NamedEntity,
)
from .widgets import MetastatWidget
from .dialogs import EntityTypeDialog

LOGGER = getLogger()


class MetastatPlugin(AbstractPlugin):
    """
    Search and import ontology metadata from an external service.
    """
    sgnProjectChanged = QtCore.pyqtSignal(str)
    sgnUpdateState = QtCore.pyqtSignal()

    def __init__(self, spec, session):
        """
        Initialises a new instance of the metadata importer plugin.
        :type spec: PluginSpec
        :type session: Session
        """
        super().__init__(spec, session)

    #############################################
    #   EVENTS
    #################################

    def eventFilter(self, source: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """
        Filters events if this object has been installed as an event filter for the watched object.
        """
        if event.type() == QtCore.QEvent.Resize:
            widget = source.widget()
            widget.redraw()
        return super().eventFilter(source, event)

    #############################################
    #   SLOTS
    #################################

    @QtCore.pyqtSlot(QtWidgets.QGraphicsScene)
    def onDiagramAdded(self, diagram):
        """
        Executed when a diagram is added to the project.
        :typw diagram: Diagram
        """
        self.debug('Connecting to diagram: %s', diagram.name)
        connect(diagram.sgnDragDropEvent, self.onDiagramDragDropEvent)
        connect(diagram.sgnModeChanged, self.onDiagramModeChanged)

    @QtCore.pyqtSlot(QtWidgets.QGraphicsScene, QtWidgets.QGraphicsSceneDragDropEvent)
    def onDiagramDragDropEvent(self, diagram, event: QtWidgets.QGraphicsSceneDragDropEvent):
        # Show entity type selection diagram
        if event.mimeData().hasFormat('application/json+metastat'):
            dialog = EntityTypeDialog(event.mimeData().text(), self.project.session)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                entity = NamedEntity.from_dict(json.loads(event.mimeData().data('application/json+metastat').data()))
                self.session.undostack.beginMacro('metastat entity drag&drop')
                subject = self.session.project.getIRI('http://www.istat.it/metastat/' + str(entity.id))
                predicate = self.session.project.getIRI('urn:x-graphol:origin')
                object_ = IRI('http://www.istat.it/metastat/')
                ast = AnnotationAssertion(subject, predicate, object_)
                cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                self.session.undostack.push(cmd)

                # Add metastat prefix if not present
                if not any([ns == 'http://www.istat.it/metastat/' for _, ns in self.project.prefixDictItems()]):
                    self.project.setPrefix('metastat', 'http://www.istat.it/metastat/')

                # Add lemmas for entity as rdfs:label
                for lemma in entity.lemma:
                    ast = AnnotationAssertion(
                        subject,
                        AnnotationAssertionProperty.Label.value,
                        lemma.value,
                        None,
                        lemma.lang,
                    )
                    cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                    self.session.undostack.push(cmd)

                # Add definitions for entity as rdfs:comment
                for definition in entity.definition:
                    ast = AnnotationAssertion(
                        subject,
                        AnnotationAssertionProperty.Comment.value,
                        definition.value,
                        None,
                        definition.lang,
                    )
                    cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                    self.session.undostack.push(cmd)

                # Add node with selected type
                snapToGrid = self.session.action('toggle_grid').isChecked()
                node = diagram.factory.create(Item.valueOf(str(dialog.button_group.checkedId())))
                node.iri = subject
                node.setPos(snap(event.scenePos(), Diagram.GridSize, snapToGrid))
                self.session.undostack.push(CommandNodeAdd(diagram, node))
                self.session.undostack.endMacro()
            else:
                event.setDropAction(QtCore.Qt.DropAction.IgnoreAction)
                event.ignore()

    @QtCore.pyqtSlot(DiagramMode)
    def onDiagramModeChanged(self, mode):
        """
        Executed when the diagram operational mode changes.
        :type mode: DiagramMode
        """
        # TODO: check if there are action to do on mode change
        pass

    @QtCore.pyqtSlot(QtWidgets.QGraphicsScene)
    def onDiagramRemoved(self, diagram):
        """
        Executed when a diagram is removed to the project.
        :typw diagram: Diagram
        """
        self.debug('Disconnecting from diagram: %s', diagram.name)
        disconnect(diagram.sgnDragDropEvent, self.onDiagramDragDropEvent)
        disconnect(diagram.sgnModeChanged, self.onDiagramModeChanged)

    @QtCore.pyqtSlot()
    def onSessionReady(self):
        """
        Executed whenever the main session completes the startup sequence.
        """
        widget = self.widget('metastat')  # type: MetastatWidget
        # CONNECT TO PROJECT SPECIFIC SIGNALS
        self.debug('Connecting to project: %s', self.project.name)
        connect(self.project.sgnDiagramAdded, self.onDiagramAdded)
        connect(self.project.sgnDiagramRemoved, self.onDiagramRemoved)
        #connect(self.project.sgnPrefixAdded, widget.onPrefixChanged)
        #connect(self.project.sgnPrefixModified, widget.onPrefixChanged)
        #connect(self.project.sgnPrefixRemoved, widget.onPrefixChanged)
        for diagram in self.project.diagrams():
            self.debug('Connecting to diagram: %s', diagram.name)
            connect(diagram.sgnDragDropEvent, self.onDiagramDragDropEvent)
            connect(diagram.sgnModeChanged, self.onDiagramModeChanged)
        #widget.onPrefixChanged()

    @QtCore.pyqtSlot()
    def doUpdateState(self):
        """
        Executed when the plugin session updates its state.
        """
        pass

    #############################################
    #   HOOKS
    #################################

    def dispose(self):
        """
        Executed whenever the plugin is going to be destroyed.
        """
        # DISCONNECT FROM ALL THE DIAGRAMS
        for diagram in self.project.diagrams():
            self.debug('Disconnecting from diagrams: %s', diagram.name)
            disconnect(diagram.sgnDragDropEvent, self.onDiagramDragDropEvent)
            disconnect(diagram.sgnModeChanged, self.onDiagramModeChanged)

        # DISCONNECT FROM CURRENT PROJECT
        widget = self.widget('metastat')  # type: MetastatWidget
        self.debug('Disconnecting from project: %s', self.project.name)
        #disconnect(self.project.sgnPrefixAdded, widget.onPrefixChanged)
        #disconnect(self.project.sgnPrefixModified, widget.onPrefixChanged)
        #disconnect(self.project.sgnPrefixRemoved, widget.onPrefixChanged)

        # DISCONNECT FROM ACTIVE SESSION
        self.debug('Disconnecting from active session')
        disconnect(self.session.sgnReady, self.onSessionReady)
        disconnect(self.session.sgnUpdateState, self.doUpdateState)

    def start(self):
        """
        Perform initialization tasks for the plugin.
        """
        # INITIALIZE THE WIDGET
        self.debug('Starting Metastat plugin')
        widget = MetastatWidget(self)
        widget.setObjectName('metastat')
        self.addWidget(widget)

        # CREATE DOCKING AREA WIDGET
        self.debug('Creating docking area widget')
        widget = DockWidget('Metastat', QtGui.QIcon(':icons/18/ic_explore_black'), self.session)
        widget.installEventFilter(self)
        widget.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea
            | QtCore.Qt.RightDockWidgetArea
            | QtCore.Qt.BottomDockWidgetArea
        )
        widget.setObjectName('metastat_dock')
        widget.setWidget(self.widget('metastat'))
        self.addWidget(widget)

        # CREATE SHORTCUTS
        action = widget.toggleViewAction()
        action.setParent(self.session)
        action.setShortcut(QtGui.QKeySequence('Alt+8'))

        # CREATE ENTRY IN VIEW MENU
        self.debug('Creating docking area widget toggle in "view" menu')
        menu = self.session.menu('view')
        menu.addAction(self.widget('metastat_dock').toggleViewAction())

        # INSTALL DOCKING AREA WIDGET
        self.debug('Installing docking area widget')
        self.session.addDockWidget(
            QtCore.Qt.LeftDockWidgetArea,
            self.widget('metastat_dock'),
        )

        # CONFIGURE SIGNAL/SLOTS
        connect(self.session.sgnReady, self.onSessionReady)
        connect(self.session.sgnUpdateState, self.doUpdateState)
