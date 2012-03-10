#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Virtualbricks - a vde/qemu gui written in python and GTK/Glade.
Copyright (C) 2011 Virtualbricks team

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; version 2.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import copy
import gobject
import os
import re
import select
import socket
import subprocess
import sys
from virtualbricks.logger import ChildLogger
from virtualbricks.link import Sock, Plug
from virtualbricks.brickconfig import BrickConfig
from virtualbricks.console import *
from virtualbricks.gui.graphics import *
from threading import Timer
from virtualbricks.errors import (BadConfig, DiskLocked, InvalidAction,
	InvalidName, Linkloop, NotConnected, UnmanagedType)


class Event(ChildLogger):
	def __init__(self, _factory, _name):
		ChildLogger.__init__(self, _factory)
		self.factory = _factory
		self.settings = self.factory.settings
		self.active = False
		self.name = _name
		self.cfg = BrickConfig()
		self.cfg.actions = list()
		self.cfg.delay = 0
		self.factory.events.append(self)
		self.gui_changed = False
		self.need_restart_to_apply_changes = False
		self._needsudo = False
		self.internal_console = None
		self.icon = Icon(self)
		self.icon.get_img() #sic
		self.factory.eventsmodel.add_event(self)
		self.on_config_changed()
		self.timer = None

	def needsudo(self):
		return self.factory.TCP is None and self._needsudo

	def help(self):
		print "Object type: " + self.get_type()
		print "Possible configuration parameter: "
		print "delay=n OR add [vb-shell command] OR addsh [host-shell command]"
		print "Example: <eventname> config delay=5"
		print "Example: <eventname> config add new switch myswitch add n wirefilter wf"
		print "Example: <eventname> config addsh touch /tmp/vbshcmd addsh cp /tmp/vbshcmd /tmp/vbshcmd1"
		print "END of help"
		print

	def get_type(self):
		return 'Event'

	def get_state(self):
		"""return state of the event"""
		if self.active:
			state = _('running')
		elif not self.configured():
			state = _('unconfigured')
		else:
			state = _('off')
		return state

	def get_cbset(self, key):
		cb = None
		try:
			if self.get_type() == 'Event':
				cb = Event.__dict__["cbset_" + key]
		except:
			cb = None
		return cb

	def change_state(self):
		if self.active:
			self.poweroff()
		else:
			self.poweron()

	def configured(self):
		return (len(self.cfg.actions) > 0 and self.cfg.delay > 0)

	def initialize(self, attrlist):
		if 'add' in attrlist and 'addsh' in attrlist:
			raise InvalidAction(_("Error: config line must contain add OR "
				"addsh."))
		elif('add' in attrlist):
			configactions = list()
			configactions = (' '.join(attrlist)).split('add')
			for action in configactions[1:]:
				action = action.strip()
				self.cfg.actions.append(VbShellCommand(action))
				self.info(_("Added vb-shell command: '%s'"), unicode(action))
		elif('addsh' in attrlist):
			configactions = list()
			configactions = (' '.join(attrlist)).split('addsh')
			for action in configactions[1:]:
				action = action.strip()
				self.cfg.actions.append(ShellCommand(action))
				self.info(_("Added host-shell command: '%s'"), unicode(action))
		else:
			for attr in attrlist:
				self.cfg.set(attr)

	def properly_connected(self):
		return True

	def get_parameters(self):
		tempstr = _("Delay") + ": %d" % int(self.cfg.delay)
		l = len(self.cfg.actions)
		if l > 0:
			tempstr += "; "+ _("Actions")+":"
			#Add actions cutting the tail if it's too long
			for s in self.cfg.actions:
				if isinstance(s, ShellCommand):
					tempstr += " \"*%s\"," % s
				else:
					tempstr += " \"%s\"," % s
			#Remove the last character
			tempstr=tempstr[0:-1]
		return tempstr

	def connect(self, endpoint):
		return True

	def disconnect(self):
		return

	def configure(self, attrlist):
		self.initialize(attrlist)
		# TODO brick should be gobject and a signal should be launched
		self.factory.eventsmodel.change_event(self)
		self.timer = Timer(float(self.cfg.delay), self.doactions, ())
		self.on_config_changed()

	############################
	########### Poweron/Poweroff
	############################
	def poweron(self):
		if not self.configured():
			print "bad config"
			raise BadConfig()
		if self.active:
			self.timer.cancel()
			self.active=False
			self.factory.emit("event-stopped", self.name)
			self.timer = Timer(float(self.cfg.delay), self.doactions, ())
		try:
			self.timer.start()
		except RuntimeError:
			pass
		self.active = True
		self.factory.emit("event-started", self.name)

	def poweroff(self):
		if not self.active:
			return
		self.timer.cancel()
		self.active = False
		#We get ready for new poweron
		self.timer = Timer(float(self.cfg.delay), self.doactions, ())
		self.factory.emit("event-stopped", self.name)

	def doactions(self):
		for action in self.cfg.actions:
			if (isinstance(action, VbShellCommand)):
				Parse(self.factory, action)
			elif (isinstance(action, ShellCommand)):
				try:
					subprocess.Popen(action, shell = True)
				except:
					self.factory.err(self, "Error: cannot execute shell command \"%s\"" % action)
					continue
#			else:
#				#it is an event
#				action.poweron()

		self.active = False
		#We get ready for new poweron
		self.timer = Timer(float(self.cfg.delay), self.doactions, ())
		self.factory.emit("event-accomplished", self.name)

	def on_config_changed(self):
		self.factory.emit("event-changed", self.name, self.factory.startup)

	#############################
	# Console related operations.
	#############################
	def has_console(self):
			return False

	def close_tty(self):
		return

