# SPDX-License-Identifier: GPL-3.0-or-later

from abc import (
    ABCMeta,
    abstractmethod,
)
import json
from typing import Any

from PyQt5 import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from eddy.core.commands.iri import CommandIRIAddAnnotationAssertion
from eddy.core.functions.misc import first
from eddy.core.functions.signals import connect
from eddy.core.output import getLogger
from eddy.core.owl import (
    AnnotationAssertion,
    AnnotationAssertionProperty,
    IRI,
    IRIRender,
    Literal,
)
from eddy.core.plugin import AbstractPlugin
from eddy.ui.fields import (
    ComboBox,
    IntegerField,
    StringField,
    TextField,
)

from .dialogs import RepositoryManagerDialog
from .model import NamedEntity
from .settings import (
    K_REPO_MONITOR,
    Repository,
)
from .style import stylesheet

LOGGER = getLogger()


def entityText(item: dict) -> str:
    """
    Returns the text for the response json object based on IRI render preferences.
    """
    settings = QtCore.QSettings()
    rendering = IRIRender(settings.value('ontology/iri/render', IRIRender.FULL.value, str))
    lang = settings.value('ontology/iri/render/language', 'en', str)

    if rendering == IRIRender.LABEL:
        lemma = first(filter(lambda i: i['lang'] == lang, item['lemma']))
        if lemma and lemma['value']:
            return lemma['value']
        else:
            LOGGER.warning('Missing lemma for lang tag: ', lang)
            return item['id']
    else:
        return item['id']


class MetastatWidget(QtWidgets.QWidget):
    """
    This class implements the widget used to browse metastat sources.
    """
    CATEGORY_TYPE_COLOR = QtGui.QColor("#BDEBF9")
    CLASSIFICATION_TYPE_COLOR = QtGui.QColor("#E6E6FA")
    UNIT_TYPE_COLOR = QtGui.QColor("#CFFFE5")
    VARIABLE_COLOR = QtGui.QColor("#FDFD96")

    sgnItemActivated = QtCore.pyqtSignal(QtGui.QStandardItem)
    sgnItemClicked = QtCore.pyqtSignal(QtGui.QStandardItem)
    sgnItemDoubleClicked = QtCore.pyqtSignal(QtGui.QStandardItem)
    sgnItemRightClicked = QtCore.pyqtSignal(QtGui.QStandardItem)

    def __init__(self, plugin: AbstractPlugin):
        """
        Initialize the metadata importer widget.
        """
        super().__init__(plugin.session)

        self.plugin = plugin
        settings = QtCore.QSettings()

        ########################################
        # ENTITY-TYPE ICONS
        ##############################

        self.variablePixmap = QtGui.QPixmap(18, 18)
        self.variablePixmap.fill(self.VARIABLE_COLOR)
        variablePainter = QtGui.QPainter(self.variablePixmap)
        variablePainter.setPen(QtCore.Qt.gray)
        variablePainter.drawText(self.variablePixmap.rect(), QtCore.Qt.AlignCenter, 'V')
        self.variableIcon = QtGui.QIcon(self.variablePixmap)
        self.unitTypePixmap = QtGui.QPixmap(18, 18)
        self.unitTypePixmap.fill(self.UNIT_TYPE_COLOR)
        unitTypePainter = QtGui.QPainter(self.unitTypePixmap)
        unitTypePainter.setPen(QtCore.Qt.gray)
        unitTypePainter.drawText(self.unitTypePixmap.rect(), QtCore.Qt.AlignCenter, 'U')
        self.unitTypeIcon = QtGui.QIcon(self.unitTypePixmap)
        self.classificationPixmap = QtGui.QPixmap(18, 18)
        self.classificationPixmap.fill(self.CLASSIFICATION_TYPE_COLOR)
        classificationPainter = QtGui.QPainter(self.classificationPixmap)
        classificationPainter.setPen(QtCore.Qt.gray)
        classificationPainter.drawText(self.unitTypePixmap.rect(), QtCore.Qt.AlignCenter, 'Cl')
        self.classificationIcon = QtGui.QIcon(self.classificationPixmap)
        self.categoryPixmap = QtGui.QPixmap(18, 18)
        self.categoryPixmap.fill(self.CATEGORY_TYPE_COLOR)
        categoryPainter = QtGui.QPainter(self.categoryPixmap)
        categoryPainter.setPen(QtCore.Qt.gray)
        categoryPainter.drawText(self.unitTypePixmap.rect(), QtCore.Qt.AlignCenter, 'Ct')
        self.categoryIcon = QtGui.QIcon(self.categoryPixmap)

        ########################################
        # REPOSITORY FIELDS
        ##############################

        self.repoButton = QtWidgets.QPushButton('Edit repositories', objectName='repo_edit_button')
        self.repoCombobox = QtWidgets.QComboBox(self)
        self.repoCombobox.addItems(map(lambda r: r.name, Repository.load()))
        self.repoCombobox.setCurrentIndex(settings.value('metastat/index', 0, int))

        ########################################
        # SEARCH FILTER FIELDS
        ##############################

        self.searchIRI = StringField(self)
        self.searchIRI.setAcceptDrops(False)
        self.searchIRI.setClearButtonEnabled(True)
        self.searchIRI.setPlaceholderText('Search in IRI...')
        self.searchLabel = QtWidgets.QLabel(self, objectName='iri_label')
        self.searchLabel.setText('IRI:')
        self.searchLabel.setMargin(1)
        self.searchLabel.setFixedWidth(80)
        self.searchLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.typeLabel = QtWidgets.QLabel(self, objectName='type_label')
        self.typeLabel.setText('Type:')
        self.typeLabel.setMargin(1)
        self.typeLabel.setFixedWidth(80)
        self.typeLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.typeField = StringField(self)
        self.typeField.setAcceptDrops(False)
        self.typeField.setClearButtonEnabled(True)
        self.typeField.setPlaceholderText('Search type...')
        self.lemmaLabel = QtWidgets.QLabel(self, objectName='lemma_label')
        self.lemmaLabel.setText('Lemma:')
        self.lemmaLabel.setMargin(1)
        self.lemmaLabel.setFixedWidth(80)
        self.lemmaLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.lemmaField = StringField(self)
        self.lemmaField.setAcceptDrops(False)
        self.lemmaField.setClearButtonEnabled(True)
        self.lemmaField.setPlaceholderText('Search in lemma...')
        self.descriptionLabel = QtWidgets.QLabel(self, objectName='description_label')
        self.descriptionLabel.setText('Description:')
        self.descriptionLabel.setMargin(1)
        self.descriptionLabel.setFixedWidth(80)
        self.descriptionLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.descriptionField = StringField(self)
        self.descriptionField.setAcceptDrops(False)
        self.descriptionField.setClearButtonEnabled(True)
        self.descriptionField.setPlaceholderText('Search in description...')
        self.ownerLabel = QtWidgets.QLabel(self, objectName='owner_label')
        self.ownerLabel.setText('Owner:')
        self.ownerLabel.setMargin(1)
        self.ownerLabel.setFixedWidth(80)
        self.ownerLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.ownerField = StringField(self)
        self.ownerField.setAcceptDrops(False)
        self.ownerField.setClearButtonEnabled(True)
        self.ownerField.setPlaceholderText('Search in project owner...')
        self.model = QtGui.QStandardItemModel(self)
        self.proxy = MetastatFilterProxyModel(self)
        self.proxy.setDynamicSortFilter(False)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy.setSortCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.proxy.setSourceModel(self.model)
        self.entityview = MetastatView(self)
        self.entityview.setModel(self.proxy)
        self.details = MetastatInfoWidget(self)

        ########################################
        # WIDGET LAYOUT
        ##############################

        self.repoLayout = QtWidgets.QHBoxLayout()
        self.repoLayout.setContentsMargins(0, 0, 0, 0)
        self.repoLayout.addWidget(self.repoCombobox)
        self.repoLayout.addWidget(self.repoButton)
        self.iriSearchLayout = QtWidgets.QHBoxLayout()
        self.iriSearchLayout.setContentsMargins(0, 0, 0, 0)
        self.iriSearchLayout.addWidget(self.searchLabel)
        self.iriSearchLayout.addWidget(self.searchIRI)
        self.typeSearchLayout = QtWidgets.QHBoxLayout()
        self.typeSearchLayout.setContentsMargins(0, 0, 0, 0)
        self.typeSearchLayout.addWidget(self.typeLabel)
        self.typeSearchLayout.addWidget(self.typeField)
        self.lemmaSearchLayout = QtWidgets.QHBoxLayout()
        self.lemmaSearchLayout.setContentsMargins(0, 0, 0, 0)
        self.lemmaSearchLayout.addWidget(self.lemmaLabel)
        self.lemmaSearchLayout.addWidget(self.lemmaField)
        self.descSearchLayout = QtWidgets.QHBoxLayout()
        self.descSearchLayout.addWidget(self.descriptionLabel)
        self.descSearchLayout.addWidget(self.descriptionField)
        self.ownerSearchLayout = QtWidgets.QHBoxLayout()
        self.ownerSearchLayout.addWidget(self.ownerLabel)
        self.ownerSearchLayout.addWidget(self.ownerField)
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.addLayout(self.repoLayout)
        self.mainLayout.addLayout(self.iriSearchLayout)
        self.mainLayout.addLayout(self.typeSearchLayout)
        self.mainLayout.addLayout(self.lemmaSearchLayout)
        self.mainLayout.addLayout(self.descSearchLayout)
        self.mainLayout.addLayout(self.ownerSearchLayout)
        self.mainLayout.addWidget(self.entityview)
        self.mainLayout.addWidget(self.details)

        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(216)
        self.setStyleSheet(stylesheet)

        connect(self.repoCombobox.currentIndexChanged, self.onRepositoryChanged)
        connect(self.repoButton.clicked, self.doEditRepositories)
        connect(self.searchIRI.textChanged, self.doFilterIRI)
        connect(self.searchIRI.returnPressed, self.onReturnPressed)
        connect(self.typeField.textChanged, self.doFilterType)
        connect(self.typeField.returnPressed, self.onReturnPressed)
        connect(self.lemmaField.textChanged, self.doFilterLemma)
        connect(self.lemmaField.returnPressed, self.onReturnPressed)
        connect(self.descriptionField.textChanged, self.doFilterDescription)
        connect(self.descriptionField.returnPressed, self.onReturnPressed)
        connect(self.ownerField.textChanged, self.doFilterOwner)
        connect(self.ownerField.returnPressed, self.onReturnPressed)
        connect(self.entityview.activated, self.onItemActivated)
        connect(self.entityview.doubleClicked, self.onItemDoubleClicked)
        connect(self.entityview.pressed, self.onItemPressed)
        connect(K_REPO_MONITOR.sgnUpdated, self.onRepositoryUpdated)
        # connect(self.sgnItemActivated, self.session.doFocusItem)
        # connect(self.sgnItemDoubleClicked, self.session.doFocusItem)
        # connect(self.sgnItemRightClicked, self.session.doFocusItem)

        # Trigger a repository fetch
        self.repoCombobox.currentIndexChanged.emit(self.repoCombobox.currentIndex())

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
                #self.details.repository = item.data().repository
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

    @QtCore.pyqtSlot(int)
    def onRepositoryChanged(self, index):
        """
        Executed when the selected repository in the combobox changes.
        """
        name = self.repoCombobox.itemText(index)
        repo = first(Repository.load(), filter_on_item=lambda i: i.name == name)
        self.model.clear()
        if repo:
            settings = QtCore.QSettings()
            settings.setValue('metastat/index', self.repoCombobox.currentIndex())
            settings.sync()
            url = QtCore.QUrl(repo.uri)
            url.setPath(f'{url.path()}')
            request = QtNetwork.QNetworkRequest(url)
            # request.setAttribute(MetadataRequest.RepositoryAttribute, repo)
            reply = self.session.nmanager.get(request)
            connect(reply.finished, self.onRequestCompleted)
        else:
            repo = None
        self.details.repository = repo
        self.details.entity = None
        self.details.stack()

    @QtCore.pyqtSlot()
    def onRepositoryUpdated(self):
        """Executed when the list of repositories is updated."""
        settings = QtCore.QSettings()
        index = settings.value('metastat/index', 0, int)
        repos = Repository.load()
        if len(repos) > 0:
            self.repoCombobox.clear()
            self.repoCombobox.addItems(map(lambda r: r.name, repos))
            self.repoCombobox.setCurrentIndex(0)
            settings.setValue('metastat/index', self.repoCombobox.currentIndex())
        else:
            self.repoCombobox.clear()
            self.repoCombobox.setCurrentIndex(-1)
            settings.remove('metastat/index')
        settings.sync()

    @QtCore.pyqtSlot()
    def doEditRepositories(self):
        """Executed to edit the list of metastat repositories."""
        dialog = RepositoryManagerDialog(self)
        dialog.open()

    @QtCore.pyqtSlot(str)
    def doFilterIRI(self, text):
        """Executed to filter items in the treeview by IRI."""
        self.proxy.setIriFilter(text)
        self.details.entity = None
        self.details.stack()

    @QtCore.pyqtSlot(str)
    def doFilterType(self, text):
        """Executed to filter items in the treeview by type."""
        self.proxy.setTypeFilter(text)
        self.details.entity = None
        self.details.stack()

    @QtCore.pyqtSlot(str)
    def doFilterLemma(self, text):
        """Executed to filter items in the treeview by lemma."""
        self.proxy.setLemmaFilter(text)
        self.details.entity = None
        self.details.stack()

    @QtCore.pyqtSlot(str)
    def doFilterDescription(self, text):
        """Executed to filter items in the treeview by description."""
        self.proxy.setDescriptionFilter(text)
        self.details.entity = None
        self.details.stack()

    @QtCore.pyqtSlot(str)
    def doFilterOwner(self, text):
        """Executed to filter items in the treeview by owner."""
        self.proxy.setOwnerFilter(text)
        self.details.entity = None
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
        #K_GRAPH.namespace_manager = NamespaceManager(Graph(), bind_namespaces='none')
        #for prefix, ns in self.project.prefixDictItems():
        #    K_GRAPH.bind(prefix, ns, override=True)
        self.redraw()

    @QtCore.pyqtSlot(str)
    def onRenderingModified(self, render):
        """
        Executed when IRI rendering changes.
        """
        settings = QtCore.QSettings()
        settings.value('ontology/iri/render', IRIRender.FULL.value)
        self.redraw()

    @QtCore.pyqtSlot()
    def onReturnPressed(self):
        """
        Executed when the Return or Enter key is pressed in the search field.
        """
        self.focusNextChild()

    @QtCore.pyqtSlot()
    def onRequestCompleted(self):
        """
        Executed when a metadata request has completed to update the widget.
        """
        reply = self.sender()
        try:
            reply.deleteLater()
            if reply.isFinished() and reply.error() == QtNetwork.QNetworkReply.NoError:
                data = json.loads(str(reply.readAll(), encoding='utf-8'))
                for d in data:
                    itemText = entityText(d)
                    if d['type'] == 'category':
                        item = QtGui.QStandardItem(self.categoryIcon, itemText)
                    elif d['type'] == 'classification':
                        item = QtGui.QStandardItem(self.classificationIcon, itemText)
                    elif d['type'] == 'unit-type':
                        item = QtGui.QStandardItem(self.unitTypeIcon, itemText)
                    elif d['type'] == 'variable':
                        item = QtGui.QStandardItem(self.variableIcon, itemText)
                    else:
                        LOGGER.warning(f'Unknown metastat type: {d["type"]}')
                        continue
                    item.setData(NamedEntity.from_dict(d))
                    self.model.appendRow(item)
            elif reply.isFinished() and reply.error() != QtNetwork.QNetworkReply.NoError:
                msg = f'Failed to retrieve metastat data: {reply.errorString()}'
                LOGGER.warning(msg)
                self.session.addNotification("""
                <b><font color="#7E0B17">ERROR</font></b>:
                Failed to retrieve metastat data.
                See System Log for details.
                """)
        except Exception as e:
            LOGGER.error(f'Failed to retrieve metastat data: {e}')
            self.session.addNotification("""
            <b><font color="#7E0B17">ERROR</font></b>:
            Failed to retrieve metastat data.
            See System Log for details.
            """)

    #############################################
    #   INTERFACE
    #################################

    def redraw(self) -> None:
        """
        Redraw the content of the widget.
        """
        self.entityview.update()
        self.details.redraw()

    def sizeHint(self):
        """
        Returns the recommended size for this widget.
        :rtype: QtCore.QSize
        """
        return QtCore.QSize(266, 216)


class MetastatView(QtWidgets.QListView):
    """
    This class implements the metastat list view.
    """
    def __init__(self, parent):
        """
        Initialize the metastat list view.
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
                    if data and isinstance(data, NamedEntity):
                        mimeData = QtCore.QMimeData()
                        buf = QtCore.QByteArray()
                        buf.append(json.dumps(data.to_dict(deep=True)))
                        mimeData.setData('application/json+metastat', buf)
                        mimeData.setText(data.id)
                        drag = QtGui.QDrag(self)
                        drag.setMimeData(mimeData)
                        drag.exec_(QtCore.Qt.DropAction.CopyAction)
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

    def update(self, index: QtCore.QModelIndex = None):
        """
        Update the view for the given index (if any).
        """
        if index:
            super().update(index)
            proxy = self.model()
            item = proxy.sourceModel().itemFromIndex(proxy.mapToSource(index))
            item.setText(entityText(item.data().to_dict(deep=True)))
            super().update()
        else:
            for row in range(self.model().rowCount()):
                index = self.model().index(row, 0)
                self.update(index)
            super().update()

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
    """Extends QSortFilterProxyModel adding filtering functionalities for the metastat widget."""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.filter_iri = ""
        self.filter_type = ""
        self.filter_lemma = ""
        self.filter_definition = ""
        self.filter_owner = ""

    def setIriFilter(self, text):
        self.filter_iri = text
        self.invalidateFilter()

    def setTypeFilter(self, text):
        # "" = no filter
        self.filter_type = text
        self.invalidateFilter()

    def setLemmaFilter(self, text):
        self.filter_lemma = text
        self.invalidateFilter()

    def setDescriptionFilter(self, text):
        self.filter_definition = text
        self.invalidateFilter()

    def setOwnerFilter(self, text):
        self.filter_owner = text
        self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        model = self.sourceModel()
        item = model.itemFromIndex(model.index(sourceRow, 0))
        data = item.data()
        if data:
            if isinstance(data, NamedEntity):
                iri = data.iri
                varType = data.type
                lemmas = data.lemma
                definitions = data.definition
                owner = data.owner
            else:
                return False
        else:
            return False

        if self.filter_iri and self.filter_iri.lower() not in iri.lower():
            return False

        if self.filter_type and self.filter_type.lower() not in varType.lower():
            return False

        if self.filter_lemma:
            lemma_contains = False
            for l in lemmas:
                if self.filter_lemma.lower() in l.value.lower():
                    lemma_contains = True
            if not lemma_contains:
                return False

        if self.filter_definition:
            description_contains = False
            for d in definitions:
                if self.filter_definition.lower() in d.value.lower():
                    description_contains = True
            if not description_contains:
                return False

        if self.filter_owner and owner.name and self.filter_owner.lower() not in owner.name.lower():
            return False

        return True

class MetastatInfoWidget(QtWidgets.QScrollArea):
    """
    This class implements the metastat detail widget.
    """
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        """
        Initialize the metastat info box.
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
        if "Lemma" in args[0] or "Description" in args[0]:
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

    def updateData(self, entity: NamedEntity) -> None:
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
        for lemma in entity.lemma:
            value, lang = lemma.value, lemma.lang
            self.metadataLayout.addRow(Key('Lemma', self), Text(value, self))
            if lang:
                self.metadataLayout.addRow(Key('Language', self), String(lang, self))
            self.metadataLayout.addItem(QtWidgets.QSpacerItem(10, 2))
        for definition in entity.definition:
            value, lang = definition.value, definition.lang
            self.metadataLayout.addRow(Key('Description', self), Text(value, self))
            if lang:
                self.metadataLayout.addRow(Key('Language', self), String(lang, self))
            self.metadataLayout.addItem(QtWidgets.QSpacerItem(10, 2))

class EmptyInfo(QtWidgets.QTextEdit):
    """
    This class implements the information box when there is no metastat repository.
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
        bgMsg = 'Click on a list item to see more info.'
        elided_text = fm.elidedText(bgMsg, QtCore.Qt.ElideRight, self.viewport().width())
        painter.drawText(self.viewport().rect(), QtCore.Qt.AlignCenter, elided_text)
        painter.restore()
