layered-yaml-attrdict-config (lya)
--------------------

YAML-based configuration module.

A set of classes I've created over time to make configuration files more
readable and easier to use in the code.


#### Basic syntax

Idea is the same as with `yaml.safe_load()` (`yaml.load()` was used before
14.06.5, see #2 for rationale behind the change) to load YAML configuration file
like this one:

	core:
	  connection:
	    # twisted endpoint syntax, see twisted.internet.endpoints.html#clientFromString
	    endpoint: tcp:host=example.com:port=6667
	    nickname: testbot
	    reconnect:
	      maxDelay: 30
	  xattr_emulation: /tmp/xattr.db

But when you use resulting nested-dicts in code, consider the difference between
`config['core']['connection']['reconnect']['maxDelay']` and
`config.core.connection.reconnect.maxDelay`.

Python dicts support only the first syntax, this module supports both.
Assigning values through attributes is also possible.


#### Recursive updates (inheritance)

I find it useful to have default parameters specified in the same format as any
configurable overrides to them - simple yaml file.

So consider this use-case:

	import lya
	cfg = lya.AttrDict.from_yaml('default.yaml')
	for path in sys.argv[1:]: cfg.update_yaml(path)
	cfg.dump(sys.stdout)

(there is also `AttrDict.update_dict` method for recursive updates from dict)

With default configuration file from the previous section shipped along with the
package as "default.yaml", you can have simple override like:

	core:
	  connection:
	    endpoint: ssl:host=some.local.host:port=6697

And above code will result in the following config (which will be dumped as
nicely-formatted yaml, as presented below):

	core:
	  connection:
	    endpoint: ssl:host=some.local.host:port=6697
	    nickname: testbot
	    reconnect:
	      maxDelay: 30
	  xattr_emulation: /tmp/xattr.db


#### Rebase

Similar to the above, but reversed, so result presented above can be produced by
taking some arbitrary configuration (AttrDict) and rebasing it on top of some
other (base) config:

	import lya
	base = lya.AttrDict.from_yaml('default.yaml')
	for path in sys.argv[1:]:
	  cfg.rebase(base)
	  print 'Config:', path
	  cfg.dump(sys.stdout)

Useful to fill-in default values for similar configuration parts
(e.g. configuration for each module or component).


#### Key ordering

Keys in python dictionaries are unordered and by default, yaml module loses any
ordering of keys in yaml dicts as well.

Strictly speaking, this is correct processing of YAML, but for most cases it is
inconvenient when instead of clear section like this one:

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

YAML files, parsed from `AttrDict.from_yaml` and `AttrDict.update_yaml` methods
have key ordering preserved, and AttrDict objects are based on OrderedDict
objects, which provide all the features of dict and preserve ordering during the
iteration like lists do.

There's no downside to it - both ordered dicts and lists can be used as usual,
if that's more desirable.


#### Flattening

Sometimes it's useful to have nested configuration (like presented above) to be
represented as flat list of key-value pairs.

Example usage can be storage of the configuration tree in a simple k-v database
(like berkdb) or comparison of configuration objects - ordered flat lists can be
easily processed by the "diff" command, tested for equality or hashed.

That is easy to do via `AttrDict.flatten` method, producing (from config above)
a list like this one:

	[ (('core', 'connection', 'endpoint'), 'ssl:host=some.local.host:port=6697'),
	  (('core', 'connection', 'nickname'), 'testbot'),
	  (('core', 'connection', 'reconnect', 'maxDelay'), 30),
	  (('core', 'xattr_emulation'), '/tmp/xattr.db') ]

Resulting list contains 2-value tuples - key tuple, containing the full path of
the value and the value object itself.


#### A note on name clashes

Methods of AttrDict object itself, like ones listed above can clash with keys in
the config file itself, in which case attribute access to config values is not
possible, i.e.:

	>>> a = lya.AttrDict(keys=1)
	>>> a.keys
	<bound method AttrDict.keys of AttrDict([('keys', 1)])>
	>>> a['keys']
	1

It's kinda-deliberate that such basic methods (like the ones from built-in dict
and listed above) are accessible by as usual attributes, though a bit
inconsistent.

With any kind of dynamic keys, just use access by key, not by attr.


#### More stuff

Some extra data-mangling methods are available via `AttrDict._` proxy object
(that allows access to all other methods as well, e.g. `a._.pop(k)`).

* `AttrDict._.apply(func, items=False, update=True)`

	Apply a function (`f(v)` or `f(k, v)` if "items" is set) to all values (on any
	level, depth-first), modifying them in-place if "update" is set.

* `AttrDict._.apply_flat(func, update=True)`

	Same as "apply" above, but passes tuple of keys forming a path to each value
	(e.g. `('a', 'b', 'c')` for value in `dict(a=dict(b=dict(c=1)))`) to `f(k, v)`.

* `AttrDict._.filter(func, items=False)`

	Same as "apply" above, but will remove values if filter function returns falsy
	value, leaving them unchanged otherwise.



Installation
--------------------

It's a regular package for Python 2.6+ and Python 3.0+.

Using [pip](http://pip-installer.org/) is the best way (see also
[pip2014](http://pip2014.com/) basic usage essentials):

	% pip install layered-yaml-attrdict-config

If you don't have it, use:

	% easy_install pip
	% pip install layered-yaml-attrdict-config

Alternatively ([see also](http://www.pip-installer.org/en/latest/installing.html)):

	% curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python
	% pip install layered-yaml-attrdict-config

Or, if you absolutely must:

	% easy_install layered-yaml-attrdict-config

But, you really shouldn't do that.

Current-git version can be installed like this:

	% pip install 'git+https://github.com/mk-fg/layered-yaml-attrdict-config.git#egg=layered-yaml-attrdict-config'

Module uses [PyYAML](http://pyyaml.org/) for processing of the actual YAML
files, but can work without it, as long as you use any methods with "yaml" in
their name, i.e. creating and using AttrDict objects like a regular dicts.


Example
--------------------

	import sys, lya

	if len(sys.argv) == 1:
	  print('Usage: {} [ config.yaml ... ]', file=sys.stderr)
	  sys.exit(1)

	cfg = lya.AttrDict.from_yaml(sys.argv[1])
	for path in sys.argv[2:]: cfg.update_yaml(path)

	cfg.dump(sys.stdout)
