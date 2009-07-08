_debug = False

try:
	import gettext
except ImportError:
	# Instally dummy identity function
	import __builtin__
	__builtin__._ = lambda x: x
else:
	package_name = "kupfer"
	localedir = "./locale"
	try:
		import version_subst
	except ImportError:
		pass
	else:
		package_name = version_subst.PACKAGE_NAME
		localedir = version_subst.LOCALEDIR
	gettext.install(package_name, localedir=localedir, codeset="UTF-8")


# to load in current locale properly for sorting etc
import locale
try:
	locale.resetlocale()
except locale.Error, e:
	pass

def get_options(default_opts=""):
	"""
	Read cli options and process --usage, --version and --debug
	return a list of other application flags with --* prefix included
	"""
	usage_string = _("Usage:")

	program_options = [
		("no-splash", _("do not present main interface on launch")),
	]
	misc_options = [
		("help", _("show usage help")),
		("version", _("show version information")),
		("debug", _("enable debug info")),
	]

	usage_string = usage_string + "\n" + "\n".join("  --%-15s  %s" % (o,h) for o,h in (program_options + misc_options))

	configure_help1 = _("To configure kupfer, edit:")
	configure_help2 = _("The default config for reference is at:")
	plugin_header = _("Available plugins:")

	from getopt import getopt, GetoptError
	from sys import argv

	from kupfer import config, plugins

	config_filename = "kupfer.cfg"
	defaults_filename = "defaults.cfg"
	conf_path = config.save_config_file(config_filename)
	defaults_path = config.get_data_file(defaults_filename)

	def make_usage_text():
		plugin_list = plugins.get_plugin_desc()
		usage_text = "\n".join((
			usage_string,
			"\n",
			configure_help1,
			"\t" + conf_path,
			configure_help2,
			"\t" + defaults_path,
			"\n",
			plugin_header,
			plugin_list,
		))
		return usage_text

	try:
		opts, args = getopt(argv[1:], "", [o for o,h in program_options] + 
				[o for o,h in misc_options])
	except GetoptError, info:
		print info
		print make_usage_text()
		raise SystemExit

	for k, v in opts:
		if k == "--help":
			print make_usage_text()
			raise SystemExit
		if k == "--version":
			print_version()
			print
			print_banner()
			raise SystemExit
		if k == "--debug":
			try:
				import debug
			except ImportError, e:
				print e
			global _debug
			_debug = True

	# return list first of tuple pair
	return [tupl[0] for tupl in opts]

def print_version():
	from . import version
	print version.PACKAGE_NAME, version.VERSION

def print_banner():
	from . import version
	var = {
		"program": version.PROGRAM_NAME, "desc": version.SHORT_DESCRIPTION,
		"website": version.WEBSITE, "copyright": version.COPYRIGHT
	}
	print _("""%(program)s: %(desc)s
	%(copyright)s
	%(website)s
	""") % var

def main():
	import sys
	from os import path

	from . import browser, data
	from . import objects, plugin
	from . import pretty, plugins, settings
	from .plugins import (load_plugin_sources, sources_attribute,
			action_decorators_attribute, text_sources_attribute)

	cli_opts = get_options()
	print_banner()
	if _debug:
		pretty.debug = _debug

	s_sources = []
	S_sources = []

	def dir_source(opt):
		abs = path.abspath(path.expanduser(opt))
		return objects.DirectorySource(abs)

	def file_source(opt, depth=1):
		abs = path.abspath(path.expanduser(opt))
		return objects.FileSource((abs,), depth)

	source_config = settings.get_config()

	text_sources = []
	action_decorators = []

	for item in source_config["Plugins"]["Catalog"]:
		s_sources.extend(load_plugin_sources(item))
		text_sources.extend(load_plugin_sources(item, text_sources_attribute))
		action_decorators.extend(load_plugin_sources(item,
			action_decorators_attribute))
	for item in source_config["Plugins"]["Direct"]:
		S_sources.extend(load_plugin_sources(item))
		text_sources.extend(load_plugin_sources(item, text_sources_attribute))
		action_decorators.extend(load_plugin_sources(item,
			action_decorators_attribute))

	dir_depth = source_config["DeepDirectories"]["Depth"]

	for item in source_config["Directories"]["Catalog"]:
		s_sources.append(dir_source(item))
	for item in source_config["DeepDirectories"]["Catalog"]:
		s_sources.append(file_source(item, dir_depth))
	for item in source_config["Directories"]["Direct"]:
		S_sources.append(dir_source(item))
	for item in source_config["DeepDirectories"]["Direct"]:
		S_sources.append(file_source(item, dir_depth))
	
	if not S_sources and not s_sources:
		print pretty.print_info(__name__, "No sources found!")

	dc = data.DataController()
	dc.set_sources(S_sources, s_sources)
	dc.register_text_sources(text_sources)
	dc.register_action_decorators(action_decorators)
	w = browser.WindowController()
	w.register_keybinding(source_config["Kupfer"]["Keybinding"])
	show_icon = not (source_config["Kupfer"]["ShowStatusIcon"].lower() not in
			("yes", "true", ))
	w.set_show_statusicon(show_icon)

	quiet = ("--no-splash" in cli_opts)
	w.main(quiet=quiet)

