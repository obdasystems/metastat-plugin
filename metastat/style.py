# SPDX-License-Identifier: GPL-3.0-or-later

stylesheet = """
/*******************************************/
/*  QComboBox                              */
/*******************************************/

QComboBox {
  background: #FFFFFF;
  border: none;
  padding: 2px 18px 2px 3px;
  selection-background-color: #D0D0D0;
  selection-color: #000000;
}
QComboBox:editable {
  background: #FFFFFF;
}
QComboBox:!editable,
QComboBox::drop-down:editable,
QComboBox:!editable:on,
QComboBox::drop-down:editable:on {
  background: #FFFFFF;
}
QComboBox::drop-down {
  subcontrol-origin: padding;
  subcontrol-position: top right;
  border-left: none;
}
QComboBox::down-arrow {
  image: url(:/icons/18/ic_arrow_drop_down_black);
}
QComboBox QAbstractItemView {
  background: #FFFFFF;
  border: none;
}

/*******************************************/
/*  QPushButton                            */
/*******************************************/

QPushButton {
  border: 1px solid #A9A9A9;
  border-radius: 0;
  color: #000000;
  font-size: 12px;
  padding: 6px 16px;
  background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
    stop: 0.0 #FDFDFD, stop: 0.3 #F8F8F8,
    stop: 0.7 #EDEDED, stop: 1.0 #EBEBEB);
}
QPushButton:focus,
QPushButton:hover,
QPushButton:hover:focus,
QPushButton:pressed,
QPushButton:pressed:focus {
  border: 1px solid #42A5F5;
  border-radius: 0;
  color: #000000;
  padding: 6px 16px;
  background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
    stop: 0.0 #FDFDFD, stop: 0.3 #F8F8F8,
    stop: 0.7 #EDEDED, stop: 1.0 #EBEBEB);
}
QPushButton:disabled {
  border: 1px solid #A9A9A9;
  border-radius: 0;
  color: #A9A9A9;
  padding: 6px 16px;
  background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
    stop: 0.0 #FDFDFD, stop: 0.3 #F8F8F8,
    stop: 0.7 #EDEDED, stop: 1.0 #EBEBEB);
}
QPushButton.flat,
QPushButton.flat:focus,
QPushButton.flat:pressed,
QPushButton.flat:pressed:focus,
QPushButton.flat:hover,
QPushButton.flat:hover:focus {
  background: #a1a1a1;
  border: 0;
  color: #000000;
  text-transform: uppercase;
}
QPushButton.flat:disabled {
  color: #A9A9A9;
  background: #777777;
  font-weight: bold;
  text-transform: uppercase;
}

QPushButton.blue,
QPushButton.blue:focus,
QPushButton.blue:pressed,
QPushButton.blue:pressed:focus {
  background: #42A5F5;
}
QPushButton.blue:hover,
QPushButton.blue:hover:focus {
  background: #68bdff;
}

/*******************************************/
/*  QLineEdit                              */
/*******************************************/

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
"""