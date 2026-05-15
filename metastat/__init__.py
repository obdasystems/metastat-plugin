# SPDX-License-Identifier: GPL-3.0-or-later

import json

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
from eddy.core.commands.iri import CommandIRIAddAnnotationAssertion
from eddy.core.commands.edges import CommandEdgeAdd
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
    IRIRender,
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
            entity = NamedEntity.from_dict(json.loads(event.mimeData().data('application/json+metastat').data()))
            dialog = EntityTypeDialog(entity, self.project.session)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
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
                # Post-drop actions depending on selected node type
                if node.Type == Item.ConceptNode:
                    # 1. If dropped on restriction on set operation nodes insert corresponding relation edges
                    for n in diagram.items(event.scenePos(), edges=False):
                        # 1.1 If dropped on a restriction node insert an inclusion edge
                        if n and n.Type in [Item.DomainRestrictionNode, Item.RangeRestrictionNode]:
                            edge = diagram.factory.create(Item.InclusionEdge, source=node, target=n)
                            self.session.undostack.push(CommandEdgeAdd(diagram, edge))
                        # 2.1 If dropped on a set operation node (and, or) insert an input edge
                        if n and n.Type in [Item.IntersectionNode, Item.DisjointUnionNode, Item.UnionNode]:
                            edge = diagram.factory.create(Item.InputEdge, source=node, target=n)
                            self.session.undostack.push(CommandEdgeAdd(diagram, edge))
                    # 2. If related entities insertion is selected import as generalization
                    if dialog.related_checkbox.isChecked():
                        hierSize = len(entity.related)
                        unionNode = diagram.factory.create(Item.UnionNode)
                        unionNode.setPos(snap(event.scenePos() + QtCore.QPoint(0, 150), Diagram.GridSize, snapToGrid))
                        isaEdge = diagram.factory.create(Item.InclusionEdge, source=unionNode, target=node)
                        self.session.undostack.push(CommandEdgeAdd(diagram, isaEdge))
                        self.session.undostack.push(CommandNodeAdd(diagram, unionNode))
                        unionPos = unionNode.pos()
                        for i in range(hierSize):
                            childNode = diagram.factory.create(Item.ConceptNode)
                            childNode.setPos(QtCore.QPointF(unionPos.x() + i * 150, unionPos.y() + 150))
                            childNode.iri = self.session.project.getIRI('http://www.istat.it/metastat/' + entity.related[i])
                            childEntity = NamedEntity.from_dict(self.widget('metastat').entities.get(entity.related[i]))

                            # Add annotations for related entity node
                            subject = childNode.iri
                            predicate = self.session.project.getIRI('urn:x-graphol:origin')
                            object_ = IRI('http://www.istat.it/metastat/')
                            ast = AnnotationAssertion(subject, predicate, object_)
                            cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                            self.session.undostack.push(cmd)

                            # Add lemmas for related entity as rdfs:label
                            for lemma in childEntity.lemma:
                                ast = AnnotationAssertion(
                                    subject,
                                    AnnotationAssertionProperty.Label.value,
                                    lemma.value,
                                    None,
                                    lemma.lang,
                                )
                                cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                                self.session.undostack.push(cmd)

                            # Add definitions for related entity as rdfs:comment
                            for definition in childEntity.definition:
                                ast = AnnotationAssertion(
                                    subject,
                                    AnnotationAssertionProperty.Comment.value,
                                    definition.value,
                                    None,
                                    definition.lang,
                                )
                                cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                                self.session.undostack.push(cmd)
                            self.session.undostack.push(CommandNodeAdd(diagram, childNode))
                            inputEdge = diagram.factory.create(Item.InputEdge, source=childNode, target=unionNode)
                            self.session.undostack.push(CommandEdgeAdd(diagram, inputEdge))
                elif node.Type == Item.RoleNode and dialog.related_checkbox.isChecked():
                    # If related entities insertion is selected import them as domain and, if available, range
                    for i, ent_id in enumerate(entity.related[:2]):
                        if i == 0:
                            restrNode = diagram.factory.create(Item.DomainRestrictionNode)
                            restrNode.setPos(snap(
                                event.scenePos() + QtCore.QPoint(-100, 0), Diagram.GridSize, snapToGrid)
                            )
                        else:
                            restrNode = diagram.factory.create(Item.RangeRestrictionNode)
                            restrNode.setPos(snap(
                                event.scenePos() + QtCore.QPoint(100, 0), Diagram.GridSize, snapToGrid)
                            )
                        inEdge = diagram.factory.create(Item.InputEdge, source=node, target=restrNode)
                        self.session.undostack.push(CommandNodeAdd(diagram, restrNode))
                        self.session.undostack.push(CommandEdgeAdd(diagram, inEdge))

                        typeNode = diagram.factory.create(Item.ConceptNode)
                        if i == 0:
                            typeNode.setPos(QtCore.QPointF(restrNode.x() - 100, restrNode.y()))
                        else:
                            typeNode.setPos(QtCore.QPointF(restrNode.x() + 100, restrNode.y()))
                        typeNode.iri = self.session.project.getIRI('http://www.istat.it/metastat/' + ent_id)
                        typeEntity = NamedEntity.from_dict(self.widget('metastat').entities.get(ent_id))

                        # Add annotations for related entity node
                        subject = typeNode.iri
                        predicate = self.session.project.getIRI('urn:x-graphol:origin')
                        object_ = IRI('http://www.istat.it/metastat/')
                        ast = AnnotationAssertion(subject, predicate, object_)
                        cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                        self.session.undostack.push(cmd)

                        # Add lemmas for related entity as rdfs:label
                        for lemma in typeEntity.lemma:
                            ast = AnnotationAssertion(
                                subject,
                                AnnotationAssertionProperty.Label.value,
                                lemma.value,
                                None,
                                lemma.lang,
                            )
                            cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                            self.session.undostack.push(cmd)

                        # Add definitions for related entity as rdfs:comment
                        for definition in typeEntity.definition:
                            ast = AnnotationAssertion(
                                subject,
                                AnnotationAssertionProperty.Comment.value,
                                definition.value,
                                None,
                                definition.lang,
                            )
                            cmd = CommandIRIAddAnnotationAssertion(self.session.project, subject, ast)
                            self.session.undostack.push(cmd)
                        self.session.undostack.push(CommandNodeAdd(diagram, typeNode))
                        isaEdge = diagram.factory.create(Item.InclusionEdge, source=restrNode, target=typeNode)
                        self.session.undostack.push(CommandEdgeAdd(diagram, isaEdge))
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

    @QtCore.pyqtSlot(str)
    def onRenderingModified(self, render):
        """Executed when the IRI rendering changes."""
        widget = self.widget('metastat')  # type: MetastatWidget
        widget.redraw()

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
        disconnect(self.session.sgnRenderingModified, self.onRenderingModified)

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
        connect(self.session.sgnRenderingModified, self.onRenderingModified)

