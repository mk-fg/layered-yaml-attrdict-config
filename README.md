layered-yaml-attrdict-config
--------------------

YAML-based configuration module.

A set of classes I've created over time to make configuration files readable and
easy to use from the code.


#### Basic syntax

Idea is the same as with yaml.load() to load YAML configuration file like this
one:

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

(there is also AttrDict.update_dict method for recursive updates from dict)

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

YAML files, parsed from AttrDict.from_yaml and AttrDict.update_yaml methods have
key ordering preserved, and AttrDict objects are based on OrderedDict objects,
which provide all the features of dict and preserve ordering during the
iteration like lists do.

There's no downside to it - both ordered dicts and lists can be used as usual,
if that's more desirable.


#### Flattening

Sometimes it's useful to have nested configuration (like presented above) to be
represented as flat list of key-value pairs.

Example usage can be storage of the configuration tree in a simple k-v database
(like berkdb) or comparison of configuration objects - ordered flat lists can be
easily processed by the "diff" command, tested for equality or hashed.

That is easy to do via AttrDict.flatten() method, producing (from config above)
a list like this one:

	- (core, connection, endpoint): ssl:host=some.local.host:port=6697
	- (core, connection, nickname): testbot
	- (core, connection, reconnect, maxDelay): 30
	- (core, xattr_emulation): /tmp/xattr.db

Resulting list contains 2-value tuples - key tuple, containing the full path of
the value and the value object itself.



Installation
--------------------

It's a regular package for Python 2.7 (not 3.X).

Using [pip](http://pip-installer.org/) is the best way:

	% pip install layered-yaml-attrdict-config

If you don't have it, use:

	% easy_install pip
	% pip install layered-yaml-attrdict-config

Alternatively ([see
also](http://www.pip-installer.org/en/latest/installing.html)):

	% curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python
	% pip install layered-yaml-attrdict-config

Or, if you absolutely must:

	% easy_install layered-yaml-attrdict-config

But, you really shouldn't do that.

Current-git version can be installed like this:

	% pip install -e 'git://github.com/mk-fg/layered-yaml-attrdict-config.git#egg=layered-yaml-attrdict-config'


Example
--------------------

	import sys, lya

	if len(sys.argv) == 1:
	  print('Usage: {} [ config.yaml ... ]', file=sys.stderr)
	  sys.exit(1)

	cfg = lya.AttrDict.from_yaml(sys.argv[1])
	for path in sys.argv[2:]: cfg.update_yaml(path)

	cfg.dump(sys.stdout)
