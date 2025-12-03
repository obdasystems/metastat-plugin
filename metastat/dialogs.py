# SPDX-License-Identifier: GPL-3.0-or-later

import textwrap

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
from eddy.core.common import HasWidgetSystem
from eddy.core.datatypes.graphol import Item
from eddy.core.functions.signals import connect
from eddy.ui.fields import StringField

from .settings import Repository


class EntityTypeDialog(QtWidgets.QDialog):
    """Dialog to select entity type in the ontology when dropped onto a diagram."""

    def __init__(self, text, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"Choose an Entity type for {text}:"))
        class_rb = QtWidgets.QRadioButton("Class")
        object_property_rb = QtWidgets.QRadioButton("Object Property")
        data_property_rb = QtWidgets.QRadioButton("Data Property")
        individual_rb = QtWidgets.QRadioButton("Individual")

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.addButton(class_rb, Item.ConceptNode)
        self.button_group.addButton(object_property_rb, Item.RoleNode)
        self.button_group.addButton(data_property_rb, Item.AttributeNode)
        self.button_group.addButton(individual_rb, Item.IndividualNode)
        for rb in [class_rb, object_property_rb, data_property_rb, individual_rb]:
            connect(rb.toggled, self.doUpdateState)
            layout.addWidget(rb)
        self.btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.btns)
        connect(self.btns.accepted, self.accept)
        connect(self.btns.rejected, self.reject)
        self.setWindowTitle("Choose Entity type")
        self.setModal(True)
        self.doUpdateState(False)

    #############################################
    #   SLOTS
    #################################

    @QtCore.pyqtSlot(bool)
    def doUpdateState(self, _checked: bool):
        selected = self.button_group.checkedButton() is not None
        self.btns.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(selected)


class RepositoryManagerDialog(QtWidgets.QDialog, HasWidgetSystem):
    """Manage repositories to fetch Metastat metadata from."""

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        """Initialize the repository manager dialog."""
        super().__init__(parent)

        table = QtWidgets.QTableWidget(0, 2, self, objectName='repository_table_widget')  # noqa
        table.setHorizontalHeaderLabels(['Name', 'Endpoint'])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionsClickable(False)
        table.horizontalHeader().setMinimumSectionSize(100)
        table.horizontalHeader().setSectionsClickable(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setSectionsClickable(False)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.addWidget(table)

        delBtn = QtWidgets.QPushButton('Remove', objectName='repository_del_button')  # noqa
        delBtn.setEnabled(False)
        connect(delBtn.clicked, self.doRemoveRepository)
        self.addWidget(delBtn)

        boxlayout = QtWidgets.QHBoxLayout()
        boxlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        boxlayout.addWidget(delBtn)
        formlayout = QtWidgets.QFormLayout()
        formlayout.addRow(self.widget('repository_table_widget'))
        formlayout.addRow(boxlayout)

        groupbox = QtWidgets.QGroupBox('Repositories', self)
        groupbox.setObjectName('repository_list_groupbox')
        groupbox.setLayout(formlayout)
        self.addWidget(groupbox)

        nameField = StringField(self, objectName='repository_name_field')
        uriField = StringField(self, objectName='repository_uri_field')
        addBtn = QtWidgets.QPushButton('Add', objectName='repository_add_button')  # noqa
        connect(addBtn.clicked, self.doAddRepository)
        self.addWidget(nameField)
        self.addWidget(uriField)
        self.addWidget(addBtn)

        boxlayout = QtWidgets.QHBoxLayout()
        boxlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        boxlayout.addWidget(addBtn)
        formlayout = QtWidgets.QFormLayout()
        formlayout.addRow(QtWidgets.QLabel('Name'), nameField)
        formlayout.addRow(QtWidgets.QLabel('URI'), uriField)
        formlayout.addRow(boxlayout)

        groupbox = QtWidgets.QGroupBox('Add Repository', self)
        groupbox.setObjectName('repository_add_groupbox')
        groupbox.setLayout(formlayout)
        self.addWidget(groupbox)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.widget('repository_list_groupbox'))
        layout.addWidget(self.widget('repository_add_groupbox'))
        widget = QtWidgets.QWidget()
        widget.setObjectName('repositories_widget')
        widget.setLayout(layout)
        self.addWidget(widget)

        self.setLayout(layout)
        self.setWindowTitle('Metastat Repositories')
        self.doReloadRepositories()
        self.setModal(True)
        self.setMinimumSize(480, 320)
        self.adjustSize()

    #############################################
    #   SLOTS
    #################################

    @QtCore.pyqtSlot()
    def doAddRepository(self):
        """Shows a dialog to insert a add a new repository."""
        nameField = self.widget('repository_name_field')  # type: StringField
        uriField = self.widget('repository_uri_field')  # type: StringField

        # Validate user input
        if len(nameField.text()) == 0:
            msgBox = QtWidgets.QMessageBox(  # noqa
                QtWidgets.QMessageBox.Warning,
                'Invalid Repository Name',
                'Please specify a repository name.',
                informativeText=textwrap.dedent("""
                The repository name can be any string that is used to easily
                reference the repository.
                """), parent=self,
            )
            msgBox.open()
        elif not QtCore.QUrl(uriField.text()).isValid():
            msgBox = QtWidgets.QMessageBox(  # noqa
                QtWidgets.QMessageBox.Warning,
                'Invalid Repository URI',
                'Please specify a valid repository URI.',
                informativeText=textwrap.dedent("""
                The repository URI is the base path at which the repository API is accessible,
                and must include protocol, domain and port (if any).

                e.g.:
                    https://example.com:5000/
                    https://example.com/myrepo/
                """),
                parent=self,
            )
            msgBox.open()
        else:
            # Add new repository
            repos = Repository.load()
            if any(map(lambda r: r.name == nameField.text(), repos)):
                msgBox = QtWidgets.QMessageBox(  # noqa
                    QtWidgets.QMessageBox.Warning,
                    'Duplicate Repository Error',
                    f'A repository named {nameField.text()} already exists.',
                    informativeText=textwrap.dedent("""
                    Repository names must be unique to avoid ambiguity in the user interface.
                    """),
                    parent=self,
                )
                msgBox.open()
            else:
                repos.append(Repository(name=nameField.text(), uri=uriField.text()))
                Repository.save(repos)
                self.doReloadRepositories()

    @QtCore.pyqtSlot()
    def doReloadRepositories(self):
        """Refresh the repository list from settings."""
        widget = self.widget('repository_table_widget')  # type: QtWidgets.QTableWidget
        widget.clearContents()
        repos = Repository.load()
        widget.setRowCount(len(repos))
        for index, repo in enumerate(repos):
            nameItem = QtWidgets.QTableWidgetItem(repo.name)
            nameItem.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
            uriItem = QtWidgets.QTableWidgetItem(repo.uri)
            uriItem.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
            widget.setItem(index, 0, nameItem)
            widget.setItem(index, 1, uriItem)
        widget.resizeColumnsToContents()
        widget.sortItems(0)
        self.widget('repository_del_button').setEnabled(len(repos) > 0)

    @QtCore.pyqtSlot()
    def doRemoveRepository(self):
        """Remove selected repositories."""
        # Delete selected repositories
        widget = self.widget('repository_table_widget')  # type: QtWidgets.QTableWidget
        selections = widget.selectedRanges()
        for sel in selections:
            for row in range(sel.bottomRow(), sel.topRow() + 1):
                widget.removeRow(row)
        # Save the current repositories list
        repos = []
        for row in range(widget.rowCount()):
            repos.append(Repository(
                name=widget.item(row, 0).text(),
                uri=widget.item(row, 1).text(),
            ))
        Repository.save(repos)
        self.doReloadRepositories()
