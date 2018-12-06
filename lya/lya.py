# -*- coding: utf-8 -*-
from __future__ import print_function

import itertools as it, operator as op, functools as ft
from collections import Mapping, Sequence, Set, OrderedDict, defaultdict
import os, sys, re, types

try: import yaml, yaml.constructor
except ImportError: pass

try: from types import StringTypes as str_types
except ImportError: str_types = str, bytes # py3


class OrderedDictYAMLLoader(yaml.SafeLoader):
	'Based on: https://gist.github.com/844388'

	def __init__(self, *args, **kwargs):
		super(OrderedDictYAMLLoader, self).__init__(*args, **kwargs)
		self.add_constructor('tag:yaml.org,2002:map', type(self).construct_yaml_map)
		self.add_constructor('tag:yaml.org,2002:omap', type(self).construct_yaml_map)

	def construct_yaml_map(self, node):
		data = OrderedDict()
		yield data
		value = self.construct_mapping(node)
		data.update(value)

	def construct_mapping(self, node, deep=False):
		if isinstance(node, yaml.MappingNode):
			self.flatten_mapping(node)
		else:
			raise yaml.constructor.ConstructorError( None, None,
				'expected a mapping node, but found {}'.format(node.id), node.start_mark )

		mapping = OrderedDict()
		for key_node, value_node in node.value:
			key = self.construct_object(key_node, deep=True) # default is to not recurse into keys
			if isinstance(key, list): key = tuple(key)
			try:
				hash(key)
			except TypeError as exc:
				raise yaml.constructor.ConstructorError( 'while constructing a mapping',
					node.start_mark, 'found unacceptable key ({})'.format(exc), key_node.start_mark )
			value = self.construct_object(value_node, deep=deep)
			mapping[key] = value
		return mapping



class AttrDict_methods(object):

	def __init__(self, obj):
		for k, v in ((k,getattr(obj,k)) for k in dir(obj)):
			if re.search(r'^(_lya__)?[^_]', k) and isinstance(v, types.MethodType):
				if k.startswith('_lya__'): k = k[6:]
				setattr(self, k, v)

class AttrDict(OrderedDict):

	def __init__(self, *argz, **kwz):
		super(AttrDict, self).__init__(*argz, **kwz)
		super(AttrDict, self).__setattr__('_', AttrDict_methods(self))

	def __setitem__(self, k, v):
		super(AttrDict, self).__setitem__(k, self.map_types(v))
	def __getattr__(self, k):
			if not (k.startswith('__') or k.startswith('_OrderedDict__')):
				try: return self[k]
				except KeyError: raise AttributeError(k)
			else: return super(AttrDict, self).__getattr__(k)
	def __setattr__(self, k, v):
		if k.startswith('_OrderedDict__'):
			return super(AttrDict, self).__setattr__(k, v)
		self[k] = v

	@classmethod
	def map_types(cls, data):
		if isinstance(data, Mapping): return cls(data)
		if isinstance(data, (list, tuple)):
			return type(data)(map(cls.map_types, data))
		return data

	@classmethod
	def from_data(cls, data=None):
		if data is None: data = dict()
		return cls(data)

	@classmethod
	def from_yaml(cls, path_or_file, if_exists=False):
		src_load = lambda src: cls.from_data(yaml.load(src, OrderedDictYAMLLoader))
		if isinstance(path_or_file, str_types):
			if if_exists and not os.path.exists(path_or_file): return cls()
			with open(path_or_file) as src: return src_load(src)
		else: return src_load(path_or_file)

	@classmethod
	def from_string(cls, yaml_str):
		return cls.from_data(yaml.load(yaml_str, OrderedDictYAMLLoader))

	@staticmethod
	def flatten_dict(data, path=tuple()):
		dst = list()
		for k,v in data.items():
			k = path + (k,)
			if isinstance(v, Mapping):
				for v in v.flatten(k): dst.append(v)
			else: dst.append((k, v))
		return dst

	def flatten(self, path=tuple()):
		return self.flatten_dict(self, path=path)

	def update_flat(self, val):
		if isinstance(val, AttrDict): val = val.flatten()
		for k,v in val:
			dst = self
			for slug in k[:-1]:
				if dst.get(slug) is None:
					dst[slug] = AttrDict()
				dst = dst[slug]
			if v is not None or not isinstance(
				dst.get(k[-1]), Mapping ): dst[k[-1]] = v

	def update_dict(self, data):
		self.update_flat(self.flatten_dict(data))

	def update_yaml(self, path, if_exists=False):
		self.update_flat(self.from_yaml(path, if_exists=if_exists))

	def clone(self):
		clone = AttrDict()
		clone.update_dict(self)
		return clone

	def rebase(self, base):
		base = base.clone()
		base.update_dict(self)
		self.clear()
		self.update_dict(base)

	def dump(self, stream):
		yaml.representer.SafeRepresenter.add_representer(
			AttrDict, yaml.representer.SafeRepresenter.represent_dict )
		yaml.representer.SafeRepresenter.add_representer(
			OrderedDict, yaml.representer.SafeRepresenter.represent_dict )
		yaml.representer.SafeRepresenter.add_representer(
			defaultdict, yaml.representer.SafeRepresenter.represent_dict )
		yaml.representer.SafeRepresenter.add_representer(
			set, yaml.representer.SafeRepresenter.represent_list )
		yaml.safe_dump( self, stream,
			default_flow_style=False, encoding='utf-8' )

	## _lya__* methods are available via "_" proxy, e.g. "a._.apply()"

	def _lya__apply(self, func, items=False, vals_only=True, update=True):
		for k,v in self.items():
			v_is_dict = isinstance(v, AttrDict)
			if v_is_dict:
				v._lya__apply(func, items=items, vals_only=vals_only, update=update)
			if not vals_only or not v_is_dict:
				v = func(v) if not items else func(k, v)
				if update: self[k] = v

	def _lya__apply_flat(self, func, update=True):
		flat = self.flatten_dict(self)
		for n, (k, v) in enumerate(flat):
			v = func(k, v)
			if update: flat[n] = k, v
		if update: self.update_flat(flat)

	def _lya__filter(self, func, items=False):
		for k,v in self.items():
			if isinstance(v, AttrDict): v._lya__filter(func, items=items)
			else:
				v = func(v) if not items else func(k, v)
				if not v: del self[k]



_no_arg = object()
def configure_logging(cfg, custom_level=None, debug=_no_arg):
	import logging, logging.config
	if debug is not _no_arg:
		if custom_level is not None:
			raise ValueError(( 'Either "custom_level" ({!r}) or "debug"'
				' ({!r}) can be specified, not both' ).format(custom_level, debug))
		custom_level = logging.DEBUG if debug else logging.WARNING
	if custom_level is None: custom_level = logging.WARNING
	if not cfg:
		logging.basicConfig(level=custom_level)
		return
	for entity in it.chain.from_iterable(it.imap(
			op.methodcaller('viewvalues'),
			[cfg] + list(cfg.get(k, dict()) for k in ['handlers', 'loggers']) )):
		if isinstance(entity, Mapping)\
			and entity.get('level') == 'custom': entity['level'] = custom_level
	logging.config.dictConfig(cfg)
	logging.captureWarnings(cfg.warnings)



if __name__ == '__main__':
	if len(sys.argv) == 1:
		print('Usage: {} [ config1.yaml ... ]', file=sys.stderr)
		sys.exit(1)

	cfg = AttrDict.from_yaml(sys.argv[1])
	for path in sys.argv[2:]: cfg.update_yaml(path)
	cfg.dump(sys.stdout)
