# -*- coding: utf-8 -*-

##########################################################################
#                                                                        #
#  Eddy: a graphical editor for the specification of Graphol ontologies  #
#  Copyright (C) 2015 Daniele Pantaleone <danielepantaleone@me.com>      #
#                                                                        #
#  This program is free software: you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation, either version 3 of the License, or     #
#  (at your option) any later version.                                   #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
#  GNU General Public License for more details.                          #
#                                                                        #
#  You should have received a copy of the GNU General Public License     #
#  along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                        #
#  #####################                          #####################  #
#                                                                        #
#  Graphol is developed by members of the DASI-lab group of the          #
#  Dipartimento di Ingegneria Informatica, Automatica e Gestionale       #
#  A.Ruberti at Sapienza University of Rome: http://www.dis.uniroma1.it  #
#                                                                        #
#     - Domenico Lembo <lembo@dis.uniroma1.it>                           #
#     - Valerio Santarelli <santarelli@dis.uniroma1.it>                  #
#     - Domenico Fabio Savo <savo@dis.uniroma1.it>                       #
#     - Daniele Pantaleone <pantaleone@dis.uniroma1.it>                  #
#     - Marco Console <console@dis.uniroma1.it>                          #
#                                                                        #
##########################################################################

from abc import (
    ABCMeta,
    abstractmethod,
)
import json
import textwrap
from typing import (
    Any,
    cast,
)

from PyQt5 import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from rdflib import Graph
from rdflib.namespace import NamespaceManager

from eddy.core.commands.iri import CommandIRIAddAnnotationAssertion
from eddy.core.datatypes.graphol import Item
from eddy.core.functions.misc import first
from eddy.core.functions.signals import connect

from eddy.core.output import getLogger
from eddy.ui.fields import (
    ComboBox,
    IntegerField,
    StringField,
    TextField,
)

from eddy.core.metadata import (
    Entity,
    MetadataRequest,
    Repository,
)

from .core import K_GRAPH, NamedEntity, LiteralValue

LOGGER = getLogger()


class MetastatWidget(QtWidgets.QWidget):
    """
    This class implements the metadata importer used to search external metadata sources.
    """
    sgnItemActivated = QtCore.pyqtSignal(QtGui.QStandardItem)
    sgnItemClicked = QtCore.pyqtSignal(QtGui.QStandardItem)
    sgnItemDoubleClicked = QtCore.pyqtSignal(QtGui.QStandardItem)
    sgnItemRightClicked = QtCore.pyqtSignal(QtGui.QStandardItem)

    def __init__(self, plugin):
        """
        Initialize the metadata importer widget.
        :type plugin: Session
        """
        super().__init__(plugin.session)

        self.plugin = plugin
        self.settings = QtCore.QSettings()
        self.iconAttribute = QtGui.QIcon(':/icons/18/ic_treeview_attribute')
        self.iconConcept = QtGui.QIcon(':/icons/18/ic_treeview_concept')
        self.iconInstance = QtGui.QIcon(':/icons/18/ic_treeview_instance')
        self.iconRole = QtGui.QIcon(':/icons/18/ic_treeview_role')
        self.iconValue = QtGui.QIcon(':/icons/18/ic_treeview_value')

        self.search = StringField(self)
        self.search.setAcceptDrops(False)
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText('Search in IRI...')
        self.search.setFixedHeight(30)
        self.searchLabel = QtWidgets.QLabel(self, objectName='iri_label')
        self.searchLabel.setText('IRI:')
        self.searchLabel.setMargin(1)
        self.searchLabel.setFixedWidth(80)
        self.searchLabel.setAlignment(QtCore.Qt.AlignRight)
        self.typeComboBoxLabel = QtWidgets.QLabel(self, objectName='type_combobox_label')
        self.typeComboBoxLabel.setText('Type:')
        self.typeComboBoxLabel.setMargin(1)
        self.typeComboBoxLabel.setFixedWidth(80)
        self.typeComboBoxLabel.setAlignment(QtCore.Qt.AlignRight)
        self.typeCombobox = ComboBox(self)
        self.typeCombobox.addItems(["", "UnitType", "Variabile", "Variabile Specifica", "classificazione"])
        self.lemmaLabel = QtWidgets.QLabel(self, objectName='lemma_label')
        self.lemmaLabel.setText('Lemma:')
        self.lemmaLabel.setMargin(1)
        self.lemmaLabel.setFixedWidth(80)
        self.lemmaLabel.setAlignment(QtCore.Qt.AlignRight)
        self.lemma = StringField(self)
        self.lemma.setAcceptDrops(False)
        self.lemma.setClearButtonEnabled(True)
        self.lemma.setPlaceholderText('Search in lemma...')
        self.lemma.setFixedHeight(30)
        self.descriptionLabel = QtWidgets.QLabel(self, objectName='description_label')
        self.descriptionLabel.setText('Description:')
        self.descriptionLabel.setMargin(1)
        self.descriptionLabel.setFixedWidth(80)
        self.descriptionLabel.setAlignment(QtCore.Qt.AlignRight)
        self.description = StringField(self)
        self.description.setAcceptDrops(False)
        self.description.setClearButtonEnabled(True)
        self.description.setPlaceholderText('Search in description...')
        self.description.setFixedHeight(30)
        self.ownerLabel = QtWidgets.QLabel(self, objectName='owner_label')
        self.ownerLabel.setText('Owner:')
        self.ownerLabel.setMargin(1)
        self.ownerLabel.setFixedWidth(80)
        self.ownerLabel.setAlignment(QtCore.Qt.AlignRight)
        self.owner = StringField(self)
        self.owner.setAcceptDrops(False)
        self.owner.setClearButtonEnabled(True)
        self.owner.setPlaceholderText('Search in project owner...')
        self.owner.setFixedHeight(30)
        self.model = QtGui.QStandardItemModel(self)
        self.proxy = MetastatFilterProxyModel(self)
        self.proxy.setDynamicSortFilter(False)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy.setSortCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.proxy.setSourceModel(self.model)
        #self.proxy.setType("")
        self.entityview = MetastatView(self)
        self.entityview.setModel(self.proxy)
        self.details = MetastatInfoWidget(self)

        self.searchLayout = QtWidgets.QHBoxLayout()
        self.searchLayout.setContentsMargins(0, 0, 0, 0)
        self.searchLayout.addWidget(self.searchLabel)
        self.searchLayout.addWidget(self.search)
        self.searchLayout2 = QtWidgets.QHBoxLayout()
        self.searchLayout2.setContentsMargins(0, 0, 0, 0)
        self.searchLayout2.addWidget(self.typeComboBoxLabel)
        self.searchLayout2.addWidget(self.typeCombobox)
        self.searchLayout3 = QtWidgets.QHBoxLayout()
        self.searchLayout3.setContentsMargins(0, 0, 0, 0)
        self.searchLayout3.addWidget(self.lemmaLabel)
        self.searchLayout3.addWidget(self.lemma)
        self.searchLayout4 = QtWidgets.QHBoxLayout()
        self.searchLayout4.addWidget(self.descriptionLabel)
        self.searchLayout4.addWidget(self.description)
        self.searchLayout5 = QtWidgets.QHBoxLayout()
        self.searchLayout5.addWidget(self.ownerLabel)
        self.searchLayout5.addWidget(self.owner)
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addLayout(self.searchLayout)
        self.mainLayout.addLayout(self.searchLayout2)
        self.mainLayout.addLayout(self.searchLayout3)
        self.mainLayout.addLayout(self.searchLayout4)
        self.mainLayout.addLayout(self.searchLayout5)
        self.mainLayout.addWidget(self.entityview)
        self.mainLayout.addWidget(self.details)
        self.setTabOrder(self.search, self.typeCombobox)
        self.setTabOrder(self.typeCombobox, self.entityview)
        self.setTabOrder(self.entityview, self.details)

        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(216)
        self.setStyleSheet("""
            QLineEdit,
            QLineEdit:editable,
            QLineEdit:hover,
            QLineEdit:pressed,
            QLineEdit:focus {
              border: none;
              border-radius: 0;
              background: #FFFFFF;
              color: #000000;
              padding: 4px 4px 4px 4px;
            }
        """)

        connect(self.entityview.activated, self.onItemActivated)
        connect(self.entityview.doubleClicked, self.onItemDoubleClicked)
        connect(self.entityview.pressed, self.onItemPressed)
        connect(self.search.textChanged, self.doFilterItemByIri)
        connect(self.search.returnPressed, self.onReturnPressed)
        #connect(self.typeCombobox.currentIndexChanged, self.doFilterItemByType)
        #connect(self.lemma.textChanged, self.doFilterItemByLemma)
        #connect(self.description.textChanged, self.doFilterItemByDescription)
        #connect(self.owner.textChanged, self.doFilterItemByOwner)
        # connect(self.sgnItemActivated, self.session.doFocusItem)
        # connect(self.sgnItemDoubleClicked, self.session.doFocusItem)
        # connect(self.sgnItemRightClicked, self.session.doFocusItem)

        self.getData()
        self.redraw()
    #############################################
    #   PROPERTIES
    #################################

    @property
    def project(self):
        """
        Returns the reference to the active project.
        :rtype: Session
        """
        return self.session.project

    @property
    def session(self):
        """
        Returns the reference to the active session.
        :rtype: Session
        """
        return self.plugin.parent()

    #############################################
    #   EVENTS
    #################################

    def paintEvent(self, paintEvent):
        """
        This is needed for the widget to pick the stylesheet.
        :type paintEvent: QPaintEvent
        """
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        painter = QtGui.QPainter(self)
        style = self.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_Widget, option, painter, self)

    #############################################
    #   SLOTS
    #################################

    @QtCore.pyqtSlot(str)
    def doFilterItemByIri(self, key):
        """
        Executed when the search box is filled with data.
        :type key: str
        """
        self.proxy.setFilterKeyColumn(0)
        self.proxy.setFilterFixedString(key)
        self.proxy.sort(QtCore.Qt.AscendingOrder)
    '''
    @QtCore.pyqtSlot(int)
    def doFilterItemByType(self, index):
        """
        Executed when the selected type in the combobox changes.
        """
        type = self.typeCombobox.itemText(index)
        self.model.clear()
        if type:
            #self.proxy.setType(type)
            self.proxy.setFilterKeyColumn(1)
            self.proxy.setFilterFixedString(type)
            self.proxy.sort(QtCore.Qt.AscendingOrder)

    @QtCore.pyqtSlot(str)
    def doFilterItemByLemma(self, key):
        """
        Executed when the search box is filled with data.
        :type key: str
        """
        self.proxy.setFilterKeyColumn(2)
        self.proxy.setFilterFixedString(key)
        self.proxy.sort(QtCore.Qt.AscendingOrder)

    @QtCore.pyqtSlot(str)
    def doFilterItemByDescription(self, key):
        """
        Executed when the search box is filled with data.
        :type key: str
        """
        self.proxy.setFilterKeyColumn(3)
        self.proxy.setFilterFixedString(key)
        self.proxy.sort(QtCore.Qt.AscendingOrder)

    @QtCore.pyqtSlot(str)
    def doFilterItemByOwner(self, key):
        """
        Executed when the search box is filled with data.
        :type key: str
        """
        self.proxy.setFilterKeyColumn(3)
        self.proxy.setFilterFixedString(key)
        self.proxy.sort(QtCore.Qt.AscendingOrder)
    '''
    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def onItemActivated(self, index):
        """
        Executed when an item in the list view is activated (e.g. by pressing Return or Enter key).
        :type index: QModelIndex
        """
        # noinspection PyArgumentList
        if QtWidgets.QApplication.mouseButtons() == QtCore.Qt.NoButton:
            item = self.model.itemFromIndex(self.proxy.mapToSource(index))
            if item:
                self.details.entity = item.data()
                self.sgnItemActivated.emit(item)
                # KEEP FOCUS ON THE TREE VIEW UNLESS SHIFT IS PRESSED
                if QtWidgets.QApplication.queryKeyboardModifiers() & QtCore.Qt.SHIFT:
                    return
                self.entityview.setFocus()
                self.details.stack()

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def onItemDoubleClicked(self, index):
        """
        Executed when an item in the list view is double-clicked.
        :type index: QModelIndex
        """
        # noinspection PyArgumentList
        if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
            item = self.model.itemFromIndex(self.proxy.mapToSource(index))
            if item:
                self.details.entity = item.data()
                self.details.repository = item.data().repository
                self.sgnItemDoubleClicked.emit(item)
                self.details.stack()

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def onItemPressed(self, index):
        """
        Executed when an item in the treeview is clicked.
        :type index: QModelIndex
        """
        # noinspection PyArgumentList
        if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.LeftButton:
            item = self.model.itemFromIndex(self.proxy.mapToSource(index))
            if item:
                self.details.entity = item.data()
                #self.details.repository = item.data().repository
                self.sgnItemDoubleClicked.emit(item)
                self.details.stack()

    @QtCore.pyqtSlot()
    @QtCore.pyqtSlot(str)
    @QtCore.pyqtSlot(str, str)
    def onPrefixChanged(self, _name: str = None, _ns: str = None):
        """
        Executed when a project prefix is changed to update the medatata namespace manager.
        """
        # There is currently no support for unbinding a namespace in rdflib,
        # so we have to resort to recreating it from scratch.
        # See: https://github.com/RDFLib/rdflib/issues/1932
        K_GRAPH.namespace_manager = NamespaceManager(Graph(), bind_namespaces='none')
        for prefix, ns in self.project.prefixDictItems():
            K_GRAPH.bind(prefix, ns, override=True)
        self.redraw()

    @QtCore.pyqtSlot()
    def onReturnPressed(self):
        """
        Executed when the Return or Enter key is pressed in the search field.
        """
        self.focusNextChild()

    def getData(self):
        url = QtCore.QUrl('https://obdasys.ddns.net/metastat')
        url.setPath(f'{url.path()}/all')
        request = QtNetwork.QNetworkRequest(url)
        reply = self.session.nmanager.get(request)
        connect(reply.finished, self.onRequestCompleted)

    @QtCore.pyqtSlot()
    def onRequestCompleted(self):
        """
        Executed when a metadata request has completed to update the widget.

        reply = self.sender()
        try:
            reply.deleteLater()
            if reply.isFinished() and reply.error() == QtNetwork.QNetworkReply.NoError:
                data = json.loads(str(reply.readAll(), encoding='utf-8'))
                entities = [NamedEntity.from_dict(d) for d in data if "iri" in d]
                for e in entities:
                    e.repository = reply.request().attribute(MetadataRequest.RepositoryAttribute)
                    try:
                        itemText = K_GRAPH.namespace_manager.curie(e.iri, generate=False)
                    except KeyError:
                        itemText = e.iri
                    item = QtGui.QStandardItem(self.iconConcept, f"{itemText}")
                    item.setData(e)
                    self.model.appendRow(item)
                self.session.statusBar().showMessage('Metadata fetch completed')
            elif reply.isFinished() and reply.error() != QtNetwork.QNetworkReply.NoError:
                msg = f'Failed to retrieve metadata: {reply.errorString()}'
                LOGGER.warning(msg)
                self.session.statusBar().showMessage(msg)
        except Exception as e:
            LOGGER.error(f'Failed to retrieve metadata: {e}')
        """
        reply = self.sender()
        try:
            reply.deleteLater()
            if reply.isFinished() and reply.error() == QtNetwork.QNetworkReply.NoError:
                data = json.loads(str(reply.readAll(), encoding='utf-8'))
                for d in data:
                    itemText = d["id"]
                    item = QtGui.QStandardItem(self.iconConcept, f"{itemText}")
                    item.setData(NamedEntity.from_dict(d))
                    self.model.appendRow(item)
            elif reply.isFinished() and reply.error() != QtNetwork.QNetworkReply.NoError:
                msg = f'Failed to retrieve metadata: {reply.errorString()}'
                LOGGER.warning(msg)
                self.session.statusBar().showMessage(msg)
        except Exception as e:
            LOGGER.error(f'Failed to retrieve metadata: {e}')

    #############################################
    #   INTERFACE
    #################################

    def redraw(self) -> None:
        """
        Redraw the content of the widget.
        """
        for index in range(self.model.rowCount()):
            item = self.model.item(index, 0)
            if isinstance(item.data(), NamedEntity):
                try:
                    itemText = K_GRAPH.namespace_manager.curie(item.data().id, generate=False)
                except ValueError:
                    itemText = item.data().id
                item.setText(itemText)
        self.entityview.update()
        self.details.redraw()

    def sizeHint(self):
        """
        Returns the recommended size for this widget.
        :rtype: QtCore.QSize
        """
        return QtCore.QSize(216, 266)


class MetastatView(QtWidgets.QListView):
    """
    This class implements the metadata importer list view.
    """
    def __init__(self, parent):
        """
        Initialize the metadata importer list view.
        :type parent: MetastatWidget
        """
        super().__init__(parent)
        self.startPos = None
        self.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setHorizontalScrollMode(QtWidgets.QTreeView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setSelectionMode(QtWidgets.QListView.SelectionMode.SingleSelection)
        self.setWordWrap(True)
        # self.setItemDelegate(MetastatItemDelegate(self))

    #############################################
    #   PROPERTIES
    #################################

    @property
    def session(self):
        """
        Returns the reference to the Session holding the Metastat widget.
        :rtype: Session
        """
        return self.widget.session

    @property
    def widget(self):
        """
        Returns the reference to the Metastat widget.
        :rtype: MetastatWidget
        """
        return self.parent()

    #############################################
    #   EVENTS
    #################################

    def mousePressEvent(self, mouseEvent):
        """
        Executed when the mouse is pressed on the treeview.
        :type mouseEvent: QMouseEvent
        """
        self.clearSelection()
        if mouseEvent.buttons() & QtCore.Qt.LeftButton:
            self.startPos = mouseEvent.pos()
        super().mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        """
        Executed when the mouse if moved while a button is being pressed.
        :type mouseEvent: QMouseEvent
        """
        if mouseEvent.buttons() & QtCore.Qt.LeftButton:
            distance = (mouseEvent.pos() - self.startPos).manhattanLength()
            if distance >= QtWidgets.QApplication.startDragDistance():
                index = first(self.selectedIndexes())
                if index:
                    model = self.model().sourceModel()
                    index = self.model().mapToSource(index)
                    item = model.itemFromIndex(index)
                    data = item.data()
                    if data:
                        if isinstance(data, NamedEntity):
                            mimeData = QtCore.QMimeData()
                            mimeData.setText(str(Item.ConceptNode.value))
                            buf = QtCore.QByteArray()
                            buf.append(data.id)
                            mimeData.setData(str(Item.ConceptNode.value), buf)
                            drag = QtGui.QDrag(self)
                            drag.setMimeData(mimeData)
                            drag.exec_(QtCore.Qt.CopyAction)

                            # Add assertion indicating source
                            from eddy.core.owl import IRI, AnnotationAssertion, AnnotationAssertionProperty, Literal
                            print(data)
                            subj = self.session.project.getIRI(str(data.id))  # type: IRI
                            pred = self.session.project.getIRI('urn:x-graphol:origin')
                            #loc = QtCore.QUrl(data.repository.uri)
                            #loc.setPath(f'{loc.path()}/entities/{data.id}'.replace('//', '/'))
                            loc = "metastat"
                            obj = IRI(loc)
                            ast = AnnotationAssertion(subj, pred, obj)
                            cmd = CommandIRIAddAnnotationAssertion(self.session.project, subj, ast)
                            self.session.undostack.push(cmd)
                            for l in data.lemmas:
                                subj = self.session.project.getIRI(str(data.id))  # type: IRI
                                pred = AnnotationAssertionProperty.Label.value
                                literal = cast(LiteralValue, l.object)
                                ast = AnnotationAssertion(subj, pred, literal.value, literal.datatype, literal.language)
                                cmd = CommandIRIAddAnnotationAssertion(self.session.project, subj, ast)
                                self.session.undostack.push(cmd)
                            for d in data.definitions:
                                subj = self.session.project.getIRI(str(data.id))  # type: IRI
                                pred = AnnotationAssertionProperty.Comment.value
                                literal = cast(LiteralValue, d.object)
                                ast = AnnotationAssertion(subj, pred, literal.value, literal.datatype, literal.language)
                                cmd = CommandIRIAddAnnotationAssertion(self.session.project, subj, ast)
                                self.session.undostack.push(cmd)

        super().mouseMoveEvent(mouseEvent)

    def paintEvent(self, event: QtGui.QPaintEvent):
        """
        Overrides paintEvent to display a placeholder text.
        """
        super().paintEvent(event)
        if self.model().rowCount() == 0:
            painter = QtGui.QPainter(self.viewport())
            painter.save()
            painter.setPen(self.palette().placeholderText().color())
            fm = self.fontMetrics()
            bgMsg = 'No Metadata Available'
            elided_text = fm.elidedText(bgMsg, QtCore.Qt.ElideRight, self.viewport().width())
            painter.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, elided_text)
            painter.restore()

    #############################################
    #   INTERFACE
    #################################

    def sizeHintForColumn(self, column):
        """
        Returns the size hint for the given column.
        This will make the column of the treeview as wide as the widget that contains the view.
        :type column: int
        :rtype: int
        """
        return max(super().sizeHintForColumn(column), self.viewport().width())


class MetastatFilterProxyModel(QtCore.QSortFilterProxyModel):
    """
    Extends QSortFilterProxyModel adding filtering functionalities for the metadata importer
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    #############################################
    #   INTERFACE
    #################################

    def filterAcceptsRow(self, sourceRow: int, sourceParent: QtCore.QModelIndex) -> bool:
        """
        Overrides filterAcceptsRow to include extra filtering conditions
        :type sourceRow: int
        :type sourceParent: QModelIndex
        :rtype: bool
        """
        return sourceParent.isValid() or super().filterAcceptsRow(sourceRow, sourceParent)

class MetastatInfoWidget(QtWidgets.QScrollArea):
    """
    This class implements the metadata detail widget.
    """
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        """
        Initialize the metadata info box.
        """
        super().__init__(parent)

        self.entity = None
        self.stacked = QtWidgets.QStackedWidget(self)
        self.stacked.setContentsMargins(0, 0, 0, 0)
        self.infoEmpty = EmptyInfo(self.stacked)
        self.infoEntity = EntityInfo(self.stacked)
        self.stacked.addWidget(self.infoEmpty)
        self.stacked.addWidget(self.infoEntity)
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumSize(QtCore.QSize(216, 120))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setWidget(self.stacked)
        self.setWidgetResizable(True)

        self.setStyleSheet("""
        MetastatInfoWidget {
          background: #FFFFFF;
        }
        MetastatInfoWidget Header {
          background: #5A5050;
          padding-left: 4px;
          color: #FFFFFF;
        }
        MetastatInfoWidget Key {
          background: #BBDEFB;
          border-top: none;
          border-right: none;
          border-bottom: 1px solid #BBDEFB;
          border-left: none;
          padding: 0 0 0 4px;
        }
        MetastatInfoWidget Button,
        MetastatInfoWidget Button:focus,
        MetastatInfoWidget Button:hover,
        MetastatInfoWidget Button:hover:focus,
        MetastatInfoWidget Button:pressed,
        MetastatInfoWidget Button:pressed:focus,
        MetastatInfoWidget Text,
        MetastatInfoWidget Integer,
        MetastatInfoWidget String,
        MetastatInfoWidget Select,
        MetastatInfoWidget Parent {
          background: #E3F2FD;
          border-top: none;
          border-right: none;
          border-bottom: 1px solid #BBDEFB !important;
          border-left: 1px solid #BBDEFB !important;
          padding: 0 0 0 4px;
          text-align:left;
        }
        MetastatInfoWidget Button::menu-indicator {
          image: none;
        }
        MetastatInfoWidget Select:!editable,
        MetastatInfoWidget Select::drop-down:editable {
          background: #FFFFFF;
        }
        MetastatInfoWidget Select:!editable:on,
        MetastatInfoWidget Select::drop-down:editable:on {
          background: #FFFFFF;
        }
        MetastatInfoWidget QCheckBox {
          background: #FFFFFF;
          spacing: 0;
          margin-left: 4px;
          margin-top: 2px;
        }
        MetastatInfoWidget QCheckBox::indicator:disabled {
          background-color: #BABABA;
        }
        """)

        scrollbar = self.verticalScrollBar()
        scrollbar.installEventFilter(self)

    #############################################
    #   EVENTS
    #################################

    def eventFilter(self, source: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """
        Filter incoming events.
        """
        if source is self.verticalScrollBar():
            if event.type() in {QtCore.QEvent.Show, QtCore.QEvent.Hide}:
                self.redraw()
        return super().eventFilter(source, event)

    #############################################
    #   INTERFACE
    #################################

    def redraw(self) -> None:
        """
        Redraw the content of the widget.
        """
        width = self.width()
        scrollbar = self.verticalScrollBar()
        if scrollbar.isVisible():
            width -= scrollbar.width()
        widget = self.stacked.currentWidget()
        widget.setFixedWidth(width)
        sizeHint = widget.sizeHint()
        height = sizeHint.height()
        self.stacked.setFixedWidth(width)
        # self.stacked.setFixedHeight(clamp(height, 0))

    def stack(self) -> None:
        """
        Set the current stacked widget.
        """
        if self.entity:
            show = self.infoEntity
            show.updateData(self.entity)
        else:
            show = self.infoEmpty

        prev = self.stacked.currentWidget()
        self.stacked.setCurrentWidget(show)
        self.redraw()
        if prev is not show:
            scrollbar = self.verticalScrollBar()
            scrollbar.setValue(0)


#############################################
#   COMPONENTS
#################################


class Header(QtWidgets.QLabel):
    """
    This class implements the header of properties section.
    """
    def __init__(self, *args: Any) -> None:
        """
        Initialize the header.
        """
        super().__init__(*args)
        self.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.setFixedHeight(24)


class Key(QtWidgets.QLabel):
    """
    This class implements the key of an info field.
    """
    def __init__(self, *args: Any) -> None:
        """
        Initialize the key.
        """
        super().__init__(*args)
        if "Value" in args[0]:
            self.setFixedSize(88, 40)
        else:
            self.setFixedSize(88, 20)


class Button(QtWidgets.QPushButton):
    """
    This class implements the button to which associate a QtWidgets.QMenu instance of an info field.
    """
    def __init__(self,  *args: Any) -> None:
        """
        Initialize the button.
        """
        super().__init__(*args)


class Integer(IntegerField):
    """
    This class implements the integer value of an info field.
    """
    def __init__(self,  *args: Any) -> None:
        """
        Initialize the field.
        """
        super().__init__(*args)
        self.setFixedHeight(20)


class String(StringField):
    """
    This class implements the string value of an info field.
    """
    def __init__(self,  *args: Any) -> None:
        """
        Initialize the field.
        """
        super().__init__(*args)
        self.setFixedHeight(20)
        self.setReadOnly(True)


class Text(TextField):
    """
    This class implements the string value of an info field.
    """
    def __init__(self,  *args: Any) -> None:
        """
        Initialize the field.
        """
        super().__init__(*args)
        self.setFixedHeight(20 * (self.document().lineCount() + 1))
        self.setReadOnly(True)


class Select(ComboBox):
    """
    This class implements the selection box of an info field.
    """
    def __init__(self,  *args: Any) -> None:
        """
        Initialize the field.
        """
        super().__init__(*args)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setScrollEnabled(False)


class Parent(QtWidgets.QWidget):
    """
    This class implements the parent placeholder to be used
    to store checkbox and radio button value fields.
    """
    def __init__(self,  *args: Any) -> None:
        """
        Initialize the field.
        """
        super().__init__(*args)
        self.setFixedHeight(20)

    def paintEvent(self, paintEvent: QtGui.QPaintEvent) -> None:
        """
        This is needed for the widget to pick the stylesheet.
        """
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        painter = QtGui.QPainter(self)
        style = self.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_Widget, option, painter, self)


#############################################
#   INFO WIDGETS
#################################

class AbstractInfo(QtWidgets.QWidget):
    """
    This class implements the base information box.
    """
    __metaclass__ = ABCMeta

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """
        Initialize the base information box.
        """
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)

    #############################################
    #   INTERFACE
    #################################

    @abstractmethod
    def updateData(self, **kwargs: Any) -> None:
        """
        Fetch new information and fill the widget with data.
        """
        pass


class EntityInfo(AbstractInfo):
    """
    This class implements the information box for entities.
    """
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """
        Initialize the generic node information box.
        """
        super().__init__(parent)

        self.entity = None
        self.ownerKey = Key('Owner', self)
        self.ownerField = String(self)
        self.ownerField.setReadOnly(True)

        self.idKey = Key('Entity ID', self)
        self.idField = String(self)
        self.idField.setReadOnly(True)

        self.iriKey = Key('Entity IRI', self)
        self.iriField = String(self)
        self.iriField.setReadOnly(True)

        self.typeKey = Key('Type', self)
        self.typeField = String(self)
        self.typeField.setReadOnly(True)

        self.nodePropHeader = Header('Entity properties', self)
        self.nodePropLayout = QtWidgets.QFormLayout()
        self.nodePropLayout.setSpacing(0)
        self.nodePropLayout.addRow(self.idKey, self.idField)
        self.nodePropLayout.addRow(self.iriKey, self.iriField)
        self.nodePropLayout.addRow(self.ownerKey, self.ownerField)
        self.nodePropLayout.addRow(self.typeKey, self.typeField)

        self.metadataHeader = Header('Entity Annotations', self)
        self.metadataLayout = QtWidgets.QFormLayout()
        self.metadataLayout.setSpacing(0)

        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setAlignment(QtCore.Qt.AlignTop)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.mainLayout.addWidget(self.nodePropHeader)
        self.mainLayout.addLayout(self.nodePropLayout)
        self.mainLayout.addWidget(self.metadataHeader)
        self.mainLayout.addLayout(self.metadataLayout)

    #############################################
    #   INTERFACE
    #################################

    def updateData(self, entity: Entity) -> None:
        """
        Fetch new information and fill the widget with data.
        """
        self.idField.setValue(entity.id)
        if entity.owner:
            self.ownerField.setValue(entity.owner.name)
        # ENTITY TYPE
        if entity.type:
            self.typeField.setValue(entity.type)

        # ENTITY ANNOTATIONS
        while self.metadataLayout.rowCount() > 0:
            self.metadataLayout.removeRow(0)
        for a in entity.lemmas:
            self.metadataLayout.addRow(Key('Property', self), String("Label", self))
            if isinstance(a.object, LiteralValue):
                literal = cast(LiteralValue, a.object)
                value, lang, dtype = literal.value, literal.language, literal.datatype
                self.metadataLayout.addRow(Key('Value', self), Text(value, self))
                if lang:
                    self.metadataLayout.addRow(Key('lang', self), String(lang, self))
                if dtype:
                    self.metadataLayout.addRow(Key('dtype', self), String(dtype.n3(), self))
            else:
                self.metadataLayout.addRow(Key('Entity', self), String(a.object.n3(), self))
            self.metadataLayout.addItem(QtWidgets.QSpacerItem(10, 2))
        for a in entity.definitions:
            self.metadataLayout.addRow(Key('Property', self), String("Comment", self))
            if isinstance(a.object, LiteralValue):
                literal = cast(LiteralValue, a.object)
                value, lang, dtype = literal.value, literal.language, literal.datatype
                self.metadataLayout.addRow(Key('Value', self), Text(value, self))
                if lang:
                    self.metadataLayout.addRow(Key('lang', self), String(lang, self))
                if dtype:
                    self.metadataLayout.addRow(Key('dtype', self), String(dtype.n3(), self))
            else:
                self.metadataLayout.addRow(Key('Entity', self), String(a.object.n3(), self))
            self.metadataLayout.addItem(QtWidgets.QSpacerItem(10, 2))

class EmptyInfo(QtWidgets.QTextEdit):
    """
    This class implements the information box when there is no metadata repository.
    """

    #############################################
    #   INTERFACE
    #################################

    def paintEvent(self, event: QtGui.QPaintEvent):
        """
        Overrides paintEvent to display a placeholder text.
        """
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())
        painter.save()
        painter.setPen(self.palette().placeholderText().color())
        fm = self.fontMetrics()
        bgMsg = textwrap.dedent("""
        Click on a list item to see more info.
        """)
        elided_text = fm.elidedText(bgMsg, QtCore.Qt.ElideRight, self.viewport().width())
        painter.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, elided_text)
        painter.restore()

class EntityTypeDialog(QtWidgets.QDialog):
    def __init__(self, text, parent: QtWidgets.QWidget = None,):
        super().__init__(parent)
        self.setWindowTitle("Choose Entity type")
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"Choose an Entity type for {text}:"))
        class_rb = QtWidgets.QRadioButton("Class")
        object_property_rb = QtWidgets.QRadioButton("Object Property")
        data_property_rb = QtWidgets.QRadioButton("Data Property")
        individual_rb = QtWidgets.QRadioButton("Individual")

        self.button_group = QtWidgets.QButtonGroup()
        self.button_group.addButton(class_rb, 65537)
        self.button_group.addButton(object_property_rb, 65539)
        self.button_group.addButton(data_property_rb, 65538)
        self.button_group.addButton(individual_rb, 65541)
        for rb in [class_rb, object_property_rb, data_property_rb, individual_rb]:
            rb.toggled.connect(self.update_buttons)
            layout.addWidget(rb)

        self.btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(self.btns)
        self.btns.accepted.connect(self.accept)
        self.btns.rejected.connect(self.reject)

        self.btns.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def update_buttons(self):
        selected = self.button_group.checkedButton() is not None
        self.btns.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(selected)