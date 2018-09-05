#!/usr/bin/python2
# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016  Simone Donadello, Carmelo Mordini
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PySide import QtCore, QtGui

class QPushButtonIndexed(QtGui.QPushButton):
    indexSignal = QtCore.Signal(int)
    nextIndexSignal = QtCore.Signal(int)
    def __init__(self, index, *args, **kwargs):
        super(QPushButtonIndexed, self).__init__(*args, **kwargs)
        self.index = index
        self.clicked.connect(self.emit_index)
        self.clicked.connect(self.emit_next_index)

    def emit_index(self):
        self.indexSignal.emit(self.index)
    def emit_next_index(self):
        self.nextIndexSignal.emit(self.index + 1)
