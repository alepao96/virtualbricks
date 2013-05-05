# Virtualbricks - a vde/qemu gui written in python and GTK/Glade.
# Copyright (C) 2013 Virtualbricks team

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import sys
import os
import os.path
import re
import logging
import pkgutil

import Image
import pygraphviz as pgv


log = logging.getLogger('virtualbricks.gui')


def get_filename(package, resource):
	loader = pkgutil.get_loader(package)
	mod = sys.modules.get(package) or loader.load_module(package)
	if mod is None or not hasattr(mod, "__file__"):
		return None
	parts = resource.split("/")
	parts.insert(0, os.path.dirname(mod.__file__))
	return os.path.join(*parts)


get_data = pkgutil.get_data


def has_custom_icon(brick):
	return "icon" in brick.cfg and brick.cfg.icon != ""


def running_brick_icon(brick):
	if not has_custom_icon(brick):
		return get_filename("virtualbricks.gui",
						"data/" + brick.get_type().lower() + ".png")
	else:
		return brick.cfg.icon


def stopped_brick_icon(brick):
	if not has_custom_icon(brick):
		return get_filename("virtualbricks.gui",
						"data/" + brick.get_type().lower() + "_gray.png")
	else:
		if "icon_gray" in brick.cfg and brick.cfg.icon_gray is not None:
			return brick.cfg.icon_gray
		if "icon" in brick.cfg and brick.cfg.icon is not None:
			return brick.cfg.icon
		return stopped_brick_icon(brick)


def is_running(brick):
	if hasattr(brick, "proc"):
		return brick.proc is not None
	elif hasattr(brick, "active"):
		return brick.active
	return True


def get_brick_icon(brick):
	if is_running(brick):
		return running_brick_icon(brick)
	else:
		return stopped_brick_icon(brick)


def get_image(name):
	return get_filename("virtualbricks.gui", "data/" + name)


class Node:
	def __init__(self, topology, name, x, y, thresh = 50):
		self.x = x
		self.y = y
		self.thresh = thresh
		self.name = name
		self.parent = topology
	def here(self, x, y):
		if abs(x + self.parent.x_adj - self.x) < self.thresh and abs(y + self.parent.y_adj - self.y) < self.thresh:
			return True
		else:
			return False

class Topology():

	def __init__(self, widget, bricks_model, scale=1.00, orientation="LR", export=None, tempdir="/tmp/"):
		self.topowidget = widget
		self.topo = pgv.AGraph()

		self.topo.graph_attr['rankdir']=orientation


		self.topo.graph_attr['ranksep']='2.0'
		self.nodes = []
		self.x_adj = 0.0
		self.y_adj = 0.0

		# Add nodes
		sg = self.topo.add_subgraph([],name="switches_rank")
		sg.graph_attr['rank'] = 'same'
		for row in bricks_model:
			b = row[0]
			self.topo.add_node(b.name)
			n = self.topo.get_node(b.name)
			n.attr['shape']='none'
			n.attr['fontsize']='9'
			n.attr['image'] = get_brick_icon(b)

		for row in bricks_model:
			b = row[0]
			loop = 0
			for e in b.plugs:
				if e.sock is not None:
					if (b.get_type() == 'Tap'):
						self.topo.add_edge(b.name, e.sock.brick.name)
						e = self.topo.get_edge(b.name, e.sock.brick.name)
					elif len(b.plugs) == 2:
						if loop == 0:
							self.topo.add_edge(e.sock.brick.name, b.name)
							e = self.topo.get_edge(e.sock.brick.name, b.name)
						else:
							self.topo.add_edge(b.name, e.sock.brick.name)
							e = self.topo.get_edge(b.name, e.sock.brick.name)
					elif loop < (len(b.plugs) + 1) / 2:
						self.topo.add_edge(e.sock.brick.name, b.name)
						e = self.topo.get_edge(e.sock.brick.name, b.name)
					else:
						self.topo.add_edge(b.name, e.sock.brick.name)
						e = self.topo.get_edge(b.name, e.sock.brick.name)
					loop+=1
					e.attr['dir'] = 'none'
					e.attr['color'] = 'black'
					e.attr['name'] = "      "
					e.attr['decorate']='true'

		#draw and save
		self.topo.write(tempdir+"vde.dot")
		self.topo.layout('dot')
		self.topo.draw(tempdir+"vde_topology.png")
		self.topo.draw(tempdir+"vde_topology.plain")

		img = Image.open(tempdir+"vde_topology.png")
		x_siz, y_siz = img.size
		for line in open(tempdir+"vde_topology.plain").readlines():
			#arg  = line.rstrip('\n').split(' ')
			arg = re.split('\s+', line.rstrip('\n'))
			if arg[0] == 'graph':
				if(float(arg[2]) != 0 and float(arg[3]) !=0 ):
					x_fact = scale * (x_siz / float(arg[2]))
					y_fact = scale * (y_siz / float(arg[3]))
				else:
					x_fact = 1
					y_fact = 1
			elif arg[0] == 'node':
				if(float(arg[2]) !=0 and float(arg[3] != 0)):
					x = scale * (x_fact * float(arg[2]))
					y = scale * (y_siz - y_fact * float(arg[3]))
				else:
					x = scale * (x_fact)
					y = scale * (y_siz - y_fact)
				self.nodes.append(Node(self, arg[1],x,y))
		# Display on the widget
		if scale < 1.00:
			img.resize((x_siz * scale, y_siz * scale)).save(tempdir+"vde_topology.png")

		self.topowidget.set_from_file(tempdir+"vde_topology.png")
		if export:
			img.save(export)

# vim: se noet :
