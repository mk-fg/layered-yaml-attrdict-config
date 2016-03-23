layered-yaml-attrdict-config (lya)
==================================

Simple YAML-based configuration module, does what it says in the name.

There are generally MUCH more advanced and well-maintained modules for similar
purpose, please see "Links" section below for a list with *some* of these.

See also "Simplier code snippets" part below for another alternative.

|

.. contents::
  :backlinks: none



Usage
-----


Basic syntax
^^^^^^^^^^^^

Idea is the same as with ``yaml.safe_load()`` (``yaml.load()`` was used before
14.06.5, see #2 for rationale behind the change) to load YAML configuration file
like this one::

  core:
    connection:
      # twisted endpoint syntax, see twisted.internet.endpoints.html#clientFromString
      endpoint: tcp:host=example.com:port=6667
      nickname: testbot
      reconnect:
        maxDelay: 30
    xattr_emulation: /tmp/xattr.db

But when you use resulting nested-dicts in code, consider the difference between
``config['core']['connection']['reconnect']['maxDelay']`` and
``config.core.connection.reconnect.maxDelay``.

Python dicts support only the first syntax, this module supports both.
Assigning values through attributes is also possible.


Recursive updates (inheritance)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

I find it useful to have default parameters specified in the same format as any
configurable overrides to them - simple yaml file.

So consider this use-case::

  import lya
  cfg = lya.AttrDict.from_yaml('default.yaml')
  for path in sys.argv[1:]: cfg.update_yaml(path)
  cfg.dump(sys.stdout)

(there is also ``AttrDict.update_dict`` method for recursive updates from dict)

With default configuration file from the previous section shipped along with the
package as "default.yaml", you can have simple override like::

  core:
    connection:
      endpoint: ssl:host=some.local.host:port=6697

And above code will result in the following config (which will be dumped as
nicely-formatted yaml, as presented below)::

  core:
    connection:
      endpoint: ssl:host=some.local.host:port=6697
      nickname: testbot
      reconnect:
        maxDelay: 30
    xattr_emulation: /tmp/xattr.db


Rebase
^^^^^^

Similar to the above, but reversed, so result presented above can be produced by
taking some arbitrary configuration (AttrDict) and rebasing it on top of some
other (base) config::

  import lya
  base = lya.AttrDict.from_yaml('default.yaml')
  for path in sys.argv[1:]:
    cfg.rebase(base)
    print 'Config:', path
    cfg.dump(sys.stdout)

Useful to fill-in default values for similar configuration parts (e.g.
configuration for each module or component).


Key ordering
^^^^^^^^^^^^

Keys in python dictionaries are unordered and by default, yaml module loses any
ordering of keys in yaml dicts as well.

Strictly speaking, this is correct processing of YAML, but for most cases it is
inconvenient when instead of clear section like this one::

  processing_order:
    receive_test:
      name: '#bot-central'
      server: testserver
    important_filter: '^important:'
    announce: '#important-news'
    debug_filter: '\(debug message\)'
    feedback: botmaster

...you have to resort to putting all the keys that need ordering into a list
just to preserve ordering.

Especially annoying if you have to access these sections by key afterwards (and
they should be unique) or you need to override some of the sections later, so
list wrapper becomes completely artificial as it have to be converted into
OrderedDict anyway.

YAML files, parsed from ``AttrDict.from_yaml`` and ``AttrDict.update_yaml``
methods have key ordering preserved, and AttrDict objects are based on
OrderedDict objects, which provide all the features of dict and preserve
ordering during the iteration like lists do.

There's no downside to it - both ordered dicts and lists can be used as usual,
if that's more desirable.


Flattening
^^^^^^^^^^

Sometimes it's useful to have nested configuration (like presented above) to be
represented as flat list of key-value pairs.

Example usage can be storage of the configuration tree in a simple k-v database
(like berkdb) or comparison of configuration objects - ordered flat lists can be
easily processed by the "diff" command, tested for equality or hashed.

That is easy to do via ``AttrDict.flatten`` method, producing (from config
above) a list like this one::

  [ (('core', 'connection', 'endpoint'), 'ssl:host=some.local.host:port=6697'),
    (('core', 'connection', 'nickname'), 'testbot'),
    (('core', 'connection', 'reconnect', 'maxDelay'), 30),
    (('core', 'xattr_emulation'), '/tmp/xattr.db') ]

Resulting list contains 2-value tuples - key tuple, containing the full path of
the value and the value object itself.


A note on name clashes
^^^^^^^^^^^^^^^^^^^^^^

Methods of AttrDict object itself, like ones listed above can clash with keys in
the config file itself, in which case attribute access to config values is not
possible, i.e.::

  >>> a = lya.AttrDict(keys=1)
  >>> a.keys
  <bound method AttrDict.keys of AttrDict([('keys', 1)])>
  >>> a['keys']
  1

It's kinda-deliberate that such basic methods (like the ones from built-in dict
and listed above) are accessible by as usual attributes, though a bit
inconsistent.

With any kind of dynamic keys, just use access by key, not by attr.


Lists and tuples inside AttrDicts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These two types (and their subclasses) are handled specially, transforming dict
values inside to AttrDicts, and wrapping all these into same sequence type.

I.e. loading this YAML::

  parsers:
    - module: icmp
    - module: tcp
      filter: port 80
    - module: udp

Will produce AttrDict with a list of AttrDict's inside, so that e.g.
``data.parsers[1].filter`` would work afterwards.

But flattening that won't flatten lists, sets, tuples or anything but the dicts
inside, and ``AttrDict.update()`` won't "merge" these types in any way, just
override previous ones for same key/path.

This is done for consistency and simplicity (same type for any subtree), but see
`github-issue-6`_ for more rationale behind it.

.. _github-issue-6: https://github.com/mk-fg/layered-yaml-attrdict-config/issues/6


More stuff
^^^^^^^^^^

Some extra data-mangling methods are available via ``AttrDict._`` proxy object
(that allows access to all other methods as well, e.g.  ``a._.pop(k)``).

-  ``AttrDict._.apply(func, items=False, update=True)``

   Apply a function (``f(v)`` or ``f(k, v)`` if "items" is set) to all values
   (on any level, depth-first), modifying them in-place if "update" is set.

-  ``AttrDict._.apply_flat(func, update=True)``

   Same as "apply" above, but passes tuple of keys forming a path to each value
   (e.g. ``('a', 'b', 'c')`` for value in ``dict(a=dict(b=dict(c=1)))``) to
   ``f(k, v)``.

-  ``AttrDict._.filter(func, items=False)``

   Same as "apply" above, but will remove values if filter function returns
   falsy value, leaving them unchanged otherwise.



Example
-------

::

  import sys, lya

  if len(sys.argv) == 1:
    print('Usage: {} [ config.yaml ... ]', file=sys.stderr)
    sys.exit(1)

  cfg = lya.AttrDict.from_yaml(sys.argv[1])
  for path in sys.argv[2:]: cfg.update_yaml(path)

  cfg.dump(sys.stdout)



Installation
------------

It's a regular package for Python 2.7+ and Python 3.0+ (though probably not
well-tested there).

Best way to install it (from PyPI_) would be to use pip_::

  % pip install layered-yaml-attrdict-config

If you don't have it, use::

  % easy_install pip
  % pip install layered-yaml-attrdict-config

Alternatively (see also `pip2014.com`_, `pip install guide`_
and `python packaging tutorial`_)::

  % curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python
  % pip install layered-yaml-attrdict-config

Current-git version can be installed like this::

  % pip install 'git+https://github.com/mk-fg/layered-yaml-attrdict-config.git#egg=layered-yaml-attrdict-config'

Note that to install stuff in system-wide PATH and site-packages, elevated
privileges are often required.
Use ``install --user``, `~/.pydistutils.cfg`_ or virtualenv_ to do unprivileged
installs into custom paths.

Module uses `PyYAML <http://pyyaml.org/>`_ for processing of the actual YAML
files, but can work without it, as long as you use any methods with "yaml" in
their name, i.e. creating and using AttrDict objects like a regular dicts.

.. _PyPI: https://pypi.python.org/pypi/Feedjack/
.. _pip: http://pip-installer.org/
.. _pip2014.com: http://pip2014.com/
.. _python packaging tutorial: https://packaging.python.org/en/latest/installing.html
.. _pip install guide: http://www.pip-installer.org/en/latest/installing.html
.. _~/.pydistutils.cfg: http://docs.python.org/install/index.html#distutils-configuration-files
.. _virtualenv: http://pypi.python.org/pypi/virtualenv



Links
-----

In an arbitrary order.

* `confit <https://github.com/sampsyo/confit>`_

  Developed with- and used in the great
  `beets <https://github.com/sampsyo/beets>`_ project.

  Features not present in this module include:

  * "An utterly sensible API resembling dictionary-and-list structures but
    providing transparent validation without lots of boilerplate code"

    No validation here, which might be a good idea when working with yaml, where
    user might be not aware of its type-parsing quirks (e.g. ``hash: 06ed1df``
    will be a string, but ``hash: 0768031`` an int).

  * "Look for configuration files in platform-specific paths"

  * "Integration with command-line arguments via argparse or optparse from the
    standard library"

* `loadconfig <https://loadconfig.readthedocs.org/>`_

  Attribute access, ordered dict values, great documentation (with tutorials),
  ``!include`` type to split configs, ``!expand`` to pull one value from the
  other config (e.g. previous layer), ``!env``, ``!read`` (load file into
  value), CLI and `CLG <https://clg.readthedocs.org/>`_ (generate argparse stuff
  from config) integration, really easy to use.

* `orderedattrdict <https://github.com/sanand0/orderedattrdict>`_

  Similar module to parse yaml configuration with attribute-access to subtrees
  and values, created - among other things - to be more PEP8-compliant and
  well-tested version of this module (see `github-pr-10`_).

  .. _github-pr-10: https://github.com/mk-fg/layered-yaml-attrdict-config/pull/10

* `layeredconfig <https://layeredconfig.readthedocs.org/>`_

  Supports a lot of source/backend formats, including e.g. etcd stores (r/w),
  not just files or env vars, writeback (to these backends) for changed values,
  last-modified auto-updating types of values, typed values in general,
  integration with argparse and much more.

  Also has attr-access and layered loading, with optional lookups for missing
  values in other configs/sections.

* `reyaml <https://github.com/ralienpp/reyaml>`_

  Adds parsing of comments (important if human-editable config gets written
  back), ability to check and produce meaningful error messages for invalid
  values, warnings/errors for accidental inline comments (e.g. when # in
  non-quoted url won't be parsed).

* `configloader <https://configloader.readthedocs.org/en/latest/>`_

  Inspired by flask.Config, has attribute access, can be updated from env and
  other configuration formats (including .py files).

* `yamlcfg <https://pypi.python.org/pypi/yamlcfg/>`_

  Implements attribute access and ordered layers, can add a highest-priority
  values from env vars.

* `yamlconfig <https://pypi.python.org/pypi/yamlconfig/>`_

  Implements basic templating from "default" values on top of YAML instead of
  layers.

* `yamlsettings <https://pypi.python.org/pypi/yamlsettings/>`_

  Can "help manage project settings, without having to worry about accidentally
  checking non-public information, like api keys".

  Same attribute access, updates, etc basic stuff.

* `python-yconfig <https://github.com/jet9/python-yconfig>`_

  Supports some code evaluation right from the YAML files, if that's your thing
  (can be really dangerous in general case, big security issue with
  e.g. ``yaml.load`` in general).



Simplier code snippets
----------------------

Much simplier alternative can be (Python 3)::

  from collections import ChainMap

  class DeepChainMap(ChainMap):
    def __init__(self, *maps, **map0):
      super(DeepChainMap, self)\
        .__init__(*filter(None, [map0] + list(maps)))
    def __getattr__(self, k):
      k_maps = list()
      for m in self.maps:
        if k in m:
          if isinstance(m[k], dict): k_maps.append(m[k])
          else: return m[k]
      if not k_maps: raise AttributeError(k)
      return DeepChainMap(*k_maps)
    def __setattr__(self, k, v):
      if k in ['maps']:
        return super(DeepChainMap, self).__setattr__(k, v)
      self[k] = v

  import yaml
  cli_opts = dict(connection=dict(port=6789))
  file_conf_a, file_conf_b = None, yaml.safe_load('connection: {host: myhost, port: null}')
  defaults = dict(connection=dict(host='localhost', port=1234, proto='tcp'))

  conf = DeepChainMap(cli_opts, file_conf_a, file_conf_b, defaults)
  print(conf.connection.host, conf.connection.port, conf.connection.proto)
  # Should print "myhost 6789 tcp", with changes to underlying maps propagating to "conf"

Similar thing I tend to use with Python-2.7 these days::

  import itertools as it, operator as op, functools as ft
  from collections import Mapping, MutableMapping

  class DeepChainMap(MutableMapping):

    _maps = None

    def __init__(self, *maps, **map0):
      self._maps = list(maps)
      if map0 or not self._maps: self._maps = [map0] + self._maps

    def __repr__(self):
      return '<DCM {:x} {}>'.format(id(self), repr(self._asdict()))

    def _asdict(self):
      return dict(it.chain.from_iterable(
        m.items() for m in reversed(self._maps) ))

    def keys(self):
      return list(it.chain.from_iterable(m.viewkeys() for m in self._maps))
    def __iter__(self): return iter(self.keys())
    def __len__(self): return len(self.keys())

    def __getitem__(self, k):
      k_maps = list()
      for m in self._maps:
        if k in m:
          if isinstance(m[k], Mapping): k_maps.append(m[k])
          elif not (m[k] is None and k_maps): return m[k]
      if not k_maps: raise KeyError(k)
      return DeepChainMap(*k_maps)

    def __getattr__(self, k):
      try: return self[k]
      except KeyError: raise AttributeError(k)

    def __setitem__(self, k, v):
      self._maps[0][k] = v

    def __setattr__(self, k, v):
      for m in map(op.attrgetter('__dict__'), [self] + self.__class__.mro()):
        if k in m:
          self.__dict__[k] = v
          break
      else: self[k] = v

    def __delitem__(self, k):
      for m in self._maps:
        if k in m: del m[k]

Please don't add 10-50 line dep modules to your code needlessly, lest we end up
with `"This kind of just broke the internet"`_ kind of mess.

.. _"This kind of just broke the internet": https://medium.com/@Rich_Harris/how-to-not-break-the-internet-with-this-one-weird-trick-e3e2d57fee28#.pbzlm4ueu
