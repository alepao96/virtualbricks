#!/usr/bin/python
# coding: utf-8

"""
Virtualbricks - a vde/qemu gui written in python and GTK/Glade.
Copyright (C) 2011 Virtualbricks team

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import functools
import gtk
import new

from virtualbricks_Logger import ChildLogger

class GUILogger(ChildLogger):
	def __init__(self):
		ChildLogger.__init__(self)

		self.messages_buffer = gtk.TextBuffer()

		tags = {
			'debug': {'foreground': '#a29898'},
			'info': { },
			'warning': {'foreground': '#ff9500'},
			'error': {'foreground': '#b8032e'},
			'critical': {'foreground': '#b8032e', 'background': '#000'},
		}

		for level, properties in tags.iteritems():
			tag = self.messages_buffer.create_tag(level)
			for property_name, value in properties.iteritems():
				tag.set_property(property_name, value)
			function = functools.partial(self._log, level=level)
			method = new.instancemethod(function, None, GUILogger)
			setattr(GUILogger, level, method)

	def _log(self, gui, text, *args, **kwargs):
		level = kwargs.pop('level')
		method = getattr(ChildLogger, level)
		method(self, text, *args, **kwargs)
		text = text % args
		iter = self.messages_buffer.get_end_iter()
		self.messages_buffer.insert_with_tags_by_name(iter, "%s\n" % text, level)

