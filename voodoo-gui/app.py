import sys

from PyQt5.QtCore import Qt, QTime, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QPushButton, QTreeView, QTreeWidget,
                             QTreeWidgetItem, QTreeWidgetItemIterator,
                             QVBoxLayout, QWidget)

from .entry import EntryItem, PropertyItem, Property, BaseEntry, EntryDelegate, EntryList, load_yaml
from .yaml_util import yaml_test


class App(QWidget):
 
    ENABLED, LABEL, DATA = range(3)
 
    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 Treeview Example - pythonspot.com'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 240
        self.initUI()
        self.show()
 
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        tree = {'root': {
                    "1": ["A", "B", "C"],
                    "2": {
                        "2-1": ["G", "H", "I"],
                        "2-2": ["J", "K", "L"]},
                    "3": ["D", "E", "F"]}
        }
        pack = load_yaml('test.yaml')
        print(pack.entries)
        print(pack.entries[2].entries)

        self.tree = QTreeWidget(self)
        layout = QHBoxLayout(self)
        layout.addWidget(self.tree)

        header=QTreeWidgetItem(["Tree","Value","Description"])
        self.tree.setHeaderItem(header)   #Another alternative is setHeaderLabels(["Tree","First",...])
        delegate = EntryDelegate()
        self.tree.setItemDelegate(delegate)
        self._populateTree(pack, self.tree.invisibleRootItem())

        def item_changed(widget_item, column=-1):
            print(column)
            if isinstance(widget_item, PropertyItem):
                widget_item.item_changed(column)
            if isinstance(widget_item, EntryItem):
                # print(widget_item.entry)
                widget_item.entry.update()
                print(f'TODO: trigger update on parent list of {widget_item.entry}')
            parent = widget_item.parent()
            if parent:
                item_changed(parent, column)
            
        self.tree.itemChanged.connect(item_changed)
        self.tree.setAlternatingRowColors(True)
        self.tree.expandToDepth(0)
        
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        # self.tree.header().setStretchLastSection(False)

        self.button = QPushButton('Build', self)
        self.button.clicked.connect(self.build)
        layout.addWidget(self.button)

    def create_entry(self, entry: BaseEntry, parent: QTreeWidgetItem):
        entry_item = QTreeWidgetItem(parent, [str(entry) or ''])
        entry_item.setFlags(entry_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
        entry_item.setFlags(entry_item.flags() ^ Qt.ItemIsEditable)
        entry_item.setCheckState(0, True)
        # type subitem, changes affect type text
        self.create_source_select(entry_item, entry)

    def _populateTree(self, data: EntryList, parent: QTreeWidgetItem):
        parent.setFlags(parent.flags() | Qt.ItemIsTristate)
        prop_list = QTreeWidgetItem(parent)
        prop_list.setFlags(prop_list.flags() ^ Qt.ItemIsUserCheckable)
        prop_list.setFlags(prop_list.flags() | Qt.ItemIsAutoTristate)
        prop_list.setText(0, 'overrides')
        prop_list.setCheckState(0, False)
        for prop_name, prop in data.overrides.items():
            prop_item = QTreeWidgetItem(prop_list)
            prop_item.setCheckState(0, Qt.Checked if prop.enabled else Qt.Unchecked)
            prop_item.setFlags(prop_item.flags() | Qt.ItemIsEditable)
            prop_item.setFlags(prop_item.flags() ^ Qt.ItemIsAutoTristate)
            prop_item.setText(0, prop_name)
            prop_item.setText(1, prop.value)
        
        for entry in data.entries:
            print(entry)
            if isinstance(entry, EntryList):
                sublist_item = QTreeWidgetItem(parent)
                sublist_item.setFlags(sublist_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                sublist_item.setText(0, f"EntryList")
                sublist_item.setCheckState(0, Qt.Unchecked)
                self._populateTree(entry, sublist_item)
            # elif isinstance(entry, BaseEntry):
            #     entry.create_widget(parent, self.tree)
            elif isinstance(entry, Property):
                entry.create_widget(parent, self.tree)
    def build(self):
        checked = self._build(self.tree.invisibleRootItem())
        print(checked)
        
        iterator = QTreeWidgetItemIterator(self.tree)

        while iterator.value():
            item = iterator.value()
            # print(item.text(0))
            self._get_parent(item, item.parent())
                
            if item.text(1) == "someText": #check value here
                item.setText(2, "text") #set text here
            iterator += 1
        pass

    def _get_parent(self, leaf: QTreeWidgetItem, item: QTreeWidgetItem):
        if not item:
            return
        parent = item.parent()
        if parent:
            self._get_parent(leaf, parent)
        print(f'{item.text(0)} {item.text(1)} {item.text(2)}')
        leaf.setText(3, leaf.text(3) + '\n' + item.text(3))

    def _build(self, parent: QTreeWidgetItem):
        checked = dict()
        print(parent)
        signal_count = parent.childCount()

        for i in range(signal_count):
            signal = parent.child(i)
            checked_sweeps = list()
            num_children = signal.childCount()

            for n in range(num_children):
                child = signal.child(n)

                if child.checkState(0) == Qt.Checked:
                    checked_sweeps.append(child.text(0))

            checked[signal.text(0)] = checked_sweeps

        return checked
    
def main():
    # yaml_test()
    # exit()
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
