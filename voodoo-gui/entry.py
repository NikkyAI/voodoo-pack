import os
import sys
from pathlib import Path

import yaml
from PyQt5.QtCore import Qt, QTime, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QGroupBox,
                             QHBoxLayout, QItemDelegate, QLabel, QLineEdit,
                             QTreeView, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)


class EntryDelegate(QItemDelegate):

    def createEditor(self, parent, option, index):
        if index.column() == 1:
            return super(EntryDelegate, self).createEditor(parent, option, index)
        return None


class PropertyItem(QTreeWidgetItem):
    '''
    Checkable entries
    '''

    def __init__(self, parent, name, prop):
        self.prop = prop
        super().__init__(parent, [name, str(self.prop.value)])
        self.setFlags(self.flags() | Qt.ItemIsEditable |
                      Qt.ItemIsUserCheckable)
        self.setCheckState(
            0, Qt.Checked if self.prop.enabled else Qt.Unchecked)

    def item_changed(self, column):
        self.prop.value = self.text(1)

class EntryItem(PropertyItem):
    '''
    Custom QTreeWidgetItem with Widgets
    '''

    def __init__(self, parent, prop, tree):
        '''
        parent (QTreeWidget) : Item's QTreeWidget parent.
        entry (BaseEntry)    : Data Entry.
        name   (str)         : Item's name. just an example.
        '''

        self.prop = prop
        self.entry = prop.value
        self.tree = tree

        # Init super class ( PropertyItem )
        super().__init__(parent, '', self.prop)

        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setFlags(self.flags() ^ Qt.ItemIsEditable)
        self.setCheckState(
            0, Qt.Checked if self.prop.enabled else Qt.Unchecked)

        self.create_source_select(self.tree)

        # Column 0 - Text:
        self.setText(0, 'Entry')
        self.setText(1, self.entry.get_name.value)

        # ## Column 1 - SpinBox:
        # self.spinBox = QtGui.QSpinBox()
        # self.spinBox.setValue( 0 )
        # self.treeWidget().setItemWidget( self, 1, self.spinBox )

        # ## Column 2 - Button:
        # self.button = QtGui.QPushButton()
        # self.button.setText( "button %s" %name )
        # self.treeWidget().setItemWidget( self, 2, self.button )

        # ## Signals
        # self.treeWidget().connect( self.button, QtCore.SIGNAL("clicked()"), self.buttonPressed )

    # @property
    # def name(self):
    #     '''
    #     Return name ( 1st column text )
    #     '''
    #     return self.text(0)

    # @property
    # def value(self):
    #     '''
    #     Return value ( 2nd column int)
    #     '''
    #     return self.spinBox.value()

    # def buttonPressed(self):
    #     '''
    #     Triggered when Item's button pressed.
    #     an example of using the Item's own values.
    #     '''
    #     print "This Item name:%s value:%i" %( self.name,
    #                                           self.value )

    def create_source_select(self, tree: QTreeWidget):

        # look up registered entries
        source = self.entry.display_name()
        type_select = QTreeWidgetItem(self, ['source', 'combobox'])
        combo_box = SourceComboBox(self.entry, self.entry._sources, self, tree)

        combo_box.setCurrentText(source)
        combo_box.currentTextChanged.emit(source)
        tree.setItemWidget(type_select, 1, combo_box)


class SourceComboBox(QComboBox):
    def __init__(self, entry, sources, entry_item: EntryItem, tree: QTreeWidget):
        super().__init__()
        self.sources = sources
        self.entry_item = entry_item
        self.tree = tree
        self.addItems(sources.keys())
        self.setCurrentText(entry.display_name())
        self.currentTextChanged.connect(self.set_text)

    @pyqtSlot(str)
    def set_text(self, string):
        self.blockSignals(True)
        self.tree.blockSignals(True)
        new_type = self.sources[string]
        new_type.clean_widget(self.entry_item)  # remove old items
        casted = new_type.__new__(new_type)
        casted.__init__(**vars(self.entry_item.entry))  # init new entry
        # print(vars(self.entry))
        # for name, value in vars(self.entry).items():
        #     casted.__setattr__(name, value)
        
        # TODO: replace old entry in entryList ?
        self.entry_item.entry = casted
        self.entry_item.prop.value = casted
        casted.populate_widget(self.entry_item, self.tree)
        self.tree.blockSignals(False)
        self.blockSignals(False)
        self.tree.itemChanged.emit(self.entry_item, 0)
        pass

    def wheelEvent(self, *args, **kwargs):
        pass


class Property(yaml.YAMLObject):
    'holds properties, can be enabled and disabled'
    yaml_tag = u'!prop'

    def __init__(self, value, enabled=True, **kwargs):
        # print(f"Property init'ed with value = {type(value).__name__} {value}")
        # allows to pass in the default enabled state for a property when setting it
        if isinstance(value, tuple) and len(value) == 2:
            enabled = value[1]
            value = value[0]
        if isinstance(value, Property):
            if hasattr(value, 'value'):
                value = value.value
        self.value = value
        self.enabled = enabled

    def __str__(self):
        return '!prop ' +str(vars(self))

    def __repr__(self):
        return str(self)
    
    # def update(self):
    #     print(f'trigger update on {self}')

    def create_widget(self, parent: QTreeWidgetItem, tree: QTreeWidget):
        if isinstance(self.value, BaseEntry):
            widget_item = EntryItem(parent, self, tree)
            # self._item = widget_item # we can send itemChanged signal manually

        # widget_item.setFlags(widget_item.flags() | Qt.ItemIsUserCheckable)
        # widget_item.setFlags(widget_item.flags() ^ Qt.ItemIsEditable)
        # widget_item.setCheckState(
        #     0, Qt.Checked if self.enabled else Qt.Unchecked)

        # self.create_source_select(widget_item, tree)

        # self.populate_widget(widget_item, parent, tree)
        return widget_item


    # def __setattr__(self, name, value):
    #     # if hasattr(self, name):
    #     #     value = super().__getattribute__(name)
    #     # else:
    #     #     value = Property(value)
    #     print(f'Property set {name} = {value}')
    #     super().__setattr__(name, value)

i = 0
class BaseEntry(yaml.YAMLObject):
    'class holding type=entry'
    yaml_tag = u'!entry'
    __sources = {}
    @property
    def _sources(self):
        return self.__sources

    fields = ['source', 'side', 'feature', 'name', 'description', ]

    # register all sources
    @classmethod
    def register(cls, othercls):
        # cls.__sources[othercls] = othercls.display_name()
        cls.__sources[othercls.display_name()] = othercls
        print(cls.__sources)

    def __init__(self, enabled=True, side='both', name='default', description='', feature=None, **kwargs):
        print('init base')
        # super().__init__(self, **kwargs)

        self.enabled = enabled
        self.side = Property(side, True)
        self.name = Property(name, True)
        self.description = Property(description, True)
        self.feature = Property(feature, False)

        # for name, default in self.properties.items():
        #     value = kwargs.get(name)
        #     if not value:
        #         value = default
        #     if name in kwargs:
        #         self.__setattr__(name, value)
        if kwargs:
            print('other values...')
            print(kwargs)
        for k, v in kwargs.items():
            print(f'setting_other {k} = {v}')
            self.__setattr__(k, v)


    @property
    def get_name(self):
        try:
            return self.name
        except AttributeError:
            self.name = Property('unnamed') # TODO: read default from dict or so
            return self.name

    # @classmethod
    # def from_yaml(cls, loader, node):
    #     """
    #     constructs the Entry (and sublcasses)
    #     and call init
    #     """
    #     data = cls.__new__(cls)
    #     data.__init__()
    #     yield data
    #     if hasattr(data, '__setstate__'):
    #         state = loader.construct_mapping(node, deep=True)
    #         data.__setstate__(state)
    #     else:
    #         state = loader.construct_mapping(node)
    #         data.__dict__.update(state)

    def __str__(self):
        return str(type(self)) + ': ' + str(vars(self))

    def __repr__(self):
        return str(type(self)) + ': ' + str(vars(self))

    def __setattr__(self, name, value):
        if hasattr(self, name):
            value = super().__getattribute__(name)
        else:
            value = Property(value)
        # print(f'set {name} {value}')
        super().__setattr__(name, value)

    @classmethod
    def display_name(cls):
        return cls.__name__.rstrip('Entry')

    def update(self):
        print(f'TODO: rebuild underlying data of {self}')
        pass

    # def create_widget(self, parent: QTreeWidgetItem, tree: QTreeWidget):
    #     widget_item = EntryItem(parent, self, tree)
    #     self._item = widget_item # we can send itemChanged signal manually

    #     # widget_item.setFlags(widget_item.flags() | Qt.ItemIsUserCheckable)
    #     # widget_item.setFlags(widget_item.flags() ^ Qt.ItemIsEditable)
    #     # widget_item.setCheckState(
    #     #     0, Qt.Checked if self.enabled else Qt.Unchecked)

    #     # self.create_source_select(widget_item, tree)

    #     # self.populate_widget(widget_item, parent, tree)
    #     return widget_item

    def populate_widget(self, widget_item: QTreeWidgetItem, tree: QTreeWidget):
        # tree.blockSignals(True)
        name_item = PropertyItem(widget_item, 'name', self.name)
        description_item = PropertyItem(widget_item, 'description', self.description)
        # tree.blockSignals(False)
        return widget_item

    @classmethod
    def clean_widget(cls, widget_item: QTreeWidgetItem):
        # TODO: remove all unlisted entries
        print(cls.fields)
        signal_count = widget_item.childCount()
        for i in range(signal_count, 0, -1):
            child = widget_item.child(i)
            if(child):
                name = child.text(0)
                if name != 'source':
                    widget_item.removeChild(child)
                # else:
                #     processed.append(name)


class CurseEntry(BaseEntry):
    'curse entry'
    yaml_tag = u'!curse'
    fields = [*BaseEntry.fields, 'id']

    def __init__(self, addon_id=0, *args, **kwargs):
        print('init curse')
        super().__init__(*args, **kwargs)
        self.addon_id = Property(addon_id, False)

    # def create_widget(self, parent: QTreeWidgetItem, tree: QTreeWidget):
    #     widget_item = super().create_widget(parent, tree)
    #     return widget_item

    def populate_widget(self, widget_item: QTreeWidgetItem, tree: QTreeWidget):
        widget_item = super().populate_widget(widget_item, tree)
        id_item = QTreeWidgetItem(
            widget_item, ['id', str(self.addon_id.value)])
        # TODO: connect to text changed signal
        id_item.setFlags(id_item.flags() | Qt.ItemIsEditable |
                         Qt.ItemIsUserCheckable)
        id_item.setCheckState(
            0, Qt.Checked if self.addon_id.enabled else Qt.Unchecked)

        return widget_item


class JenkinsEntry(BaseEntry):
    'jenkins entry'
    yaml_tag = u'!jenkins'
    fields = [*BaseEntry.fields, 'job']

    def __init__(self, job='', *args, **kwargs):
        print('init jenkins')
        super().__init__(*args, **kwargs)
        self.job = Property(job, True)

    # def create_widget(self, parent: QTreeWidgetItem, tree: QTreeWidget):
    #     widget_item = super().create_widget(parent, tree)
    #     return widget_item

    def populate_widget(self, widget_item: QTreeWidgetItem, tree: QTreeWidget):
        widget_item = super().populate_widget(widget_item, tree)
        job_item = QTreeWidgetItem(widget_item, ['job', str(self.job.value)])
        # TODO: connect to text changed signal
        job_item.setFlags(job_item.flags() |
                          Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
        job_item.setCheckState(
            0, Qt.Checked if self.job.enabled else Qt.Unchecked)
        return widget_item


class EntryList(yaml.YAMLObject):
    'class holding type=list'
    yaml_tag = u'!list'

    @classmethod
    def load(cls, path: Path):
        with open(path) as stream:
            data = yaml.load(stream)
        typ = data.get('type')
        if typ == 'list':
            return EntryList(**data)

    _file = None  # if this is the root included from a file

    def __init__(self, entries, overrides={}):
        self.entries = entries
        self.overrides = overrides

        # for entry in entries:
        #     typ = entry.get('typ')

    def __str__(self):
        return str(type(self)) + ': ' + str(vars(self))

    def __repr__(self):
        # return f'ListTag(entries={self.entries}, overrides={self.overrides})'
        return str(self)


def load_yaml(path: Path):
    # # Required for safe_load
    # yaml.SafeLoader.add_constructor('!list', EntryList.from_yaml)
    # # Required for safe_dump
    # yaml.SafeDumper.add_multi_representer(EntryList, EntryList.to_yaml)

    # # Required for safe_load
    # yaml.SafeLoader.add_constructor('!entry', Entry.from_yaml)
    # # Required for safe_dump
    # yaml.SafeDumper.add_multi_representer(Entry, Entry.to_yaml)

    # # Required for safe_load
    # yaml.SafeLoader.add_constructor('!prop', Property.from_yaml)
    # # Required for safe_dump
    # yaml.SafeDumper.add_multi_representer(Property, Property.to_yaml)

    with open(path, 'r') as stream:
        data = yaml.safe_load(stream)
    return data


BaseEntry.register(CurseEntry)
BaseEntry.register(JenkinsEntry)

# Required for safe_load
yaml.SafeLoader.add_constructor(EntryList.yaml_tag, EntryList.from_yaml)
# Required for safe_dump
yaml.SafeDumper.add_multi_representer(EntryList, EntryList.to_yaml)

# # Required for safe_load
# yaml.SafeLoader.add_constructor(BaseEntry.yaml_tag, BaseEntry.from_yaml)
# # Required for safe_dump
# yaml.SafeDumper.add_multi_representer(BaseEntry, BaseEntry.to_yaml)

# Required for safe_load
yaml.SafeLoader.add_constructor(CurseEntry.yaml_tag, CurseEntry.from_yaml)
# Required for safe_dump
yaml.SafeDumper.add_multi_representer(CurseEntry, CurseEntry.to_yaml)
# Required for safe_load
yaml.SafeLoader.add_constructor(JenkinsEntry.yaml_tag, JenkinsEntry.from_yaml)
# Required for safe_dump
yaml.SafeDumper.add_multi_representer(JenkinsEntry, JenkinsEntry.to_yaml)

# Required for safe_load
yaml.SafeLoader.add_constructor(Property.yaml_tag, Property.from_yaml)
# Required for safe_dump
yaml.SafeDumper.add_multi_representer(Property, Property.to_yaml)
