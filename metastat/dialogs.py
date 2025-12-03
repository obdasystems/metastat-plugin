# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)
from eddy.core.datatypes.graphol import Item
from eddy.core.functions.signals import connect


class EntityTypeDialog(QtWidgets.QDialog):
    def __init__(self, text, parent: QtWidgets.QWidget = None, ):
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
        self.button_group.addButton(class_rb, Item.ConceptNode)
        self.button_group.addButton(object_property_rb, Item.RoleNode)
        self.button_group.addButton(data_property_rb, Item.AttributeNode)
        self.button_group.addButton(individual_rb, Item.IndividualNode)
        for rb in [class_rb, object_property_rb, data_property_rb, individual_rb]:
            connect(rb.toggled, self.update_buttons)
            layout.addWidget(rb)

        self.btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(self.btns)
        connect(self.btns.accepted, self.accept)
        connect(self.btns.rejected, self.reject)

        self.btns.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def update_buttons(self):
        selected = self.button_group.checkedButton() is not None
        self.btns.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(selected)
