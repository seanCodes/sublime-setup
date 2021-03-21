import sublime
import sublime_plugin
import re
from os import path



FILE_PATH_REGEX = re.compile(r'^(?P<app_folder_path>(?P<app_path>.*?/)(?P<app_folder>app/|addon/|tests/))(?P<file_folder>[^/]+/)(?P<file_path>.*?(?=[^/]+$))(?P<file_name>[^.]+)\.(?P<file_type>.*)$')
STYLE_FILE_TYPES = ['.css', '.less', '.scss', '.sass', '.styl']



def get_file_type_paths_for(path, file_types):
	return [path + type for type in file_types]



class EmberNavigatorCommand(sublime_plugin.WindowCommand):


	def run(self, open_file_type='', new_tab=False):
		if not self.window.active_view().file_name():
			return sublime.status_message('File is not yet saved!')

		# Process File

		self.process_file()

		if not self.file_path_match:
			return sublime.status_message('File is not in an ember project app/*/ addon/*/ or tests/*/ directory!')

		# Determine Companion Files

		files = self.get_companion_files(open_file_type)

		if len(files) == 0:
			return sublime.status_message('No matching companion file(s) to open!')

		# Open Companion Files

		if new_tab:
			self.window.focus_group(1)

		for file in files:
			self.window.open_file(file)


	def process_file(self):
		self.file = self.window.active_view().file_name()            # /Users/user/app/templates/components/foo/foo-bar.hbs

		print('\n           file:', self.file) # DEBUG

		self.file_path_match = FILE_PATH_REGEX.search(self.file)

		if not self.file_path_match:
			print('\nFILE DOES NOT MATCH FILE PATH REGEX\n') # DEBUG
			return

		self.app_folder_path = self.file_path_match.group('app_folder_path') # /Users/username/dev/project/app/
		self.app_path        = self.file_path_match.group('app_path')        # /Users/username/dev/project/
		self.app_folder      = self.file_path_match.group('app_folder')      #                             app/
		self.file_folder     = self.file_path_match.group('file_folder')     #                                 components/
		self.file_path       = self.file_path_match.group('file_path')       #                                            foo/bar/
		self.file_name       = self.file_path_match.group('file_name')       #                                                    baz
		self.file_type       = self.file_path_match.group('file_type')       #                                                       js

		print('app_folder_path:', self.app_folder_path) # DEBUG
		print('       app_path:', self.app_path) # DEBUG
		print('     app_folder: %s%s' % (' ' * len(self.app_path), self.app_folder)) # DEBUG
		print('    file_folder: %s%s' % (' ' * len(self.app_path + self.app_folder), self.file_folder)) # DEBUG
		print('      file_path: %s%s' % (' ' * len(self.app_path + self.app_folder + self.file_folder), self.file_path)) # DEBUG
		print('      file_name: %s%s' % (' ' * len(self.app_path + self.app_folder + self.file_folder + self.file_path), self.file_name)) # DEBUG
		print('      file_type: %s%s' % (' ' * len(self.app_path + self.app_folder + self.file_folder + self.file_path + self.file_name + ' '), self.file_type)) # DEBUG


	def get_companion_files(self, open_file_type=''):
		app_folder_path = self.app_folder_path
		app_path        = self.app_path
		app_folder      = self.app_folder
		file_folder     = self.file_folder
		file_path       = self.file_path
		file_name       = self.file_name
		file_type       = self.file_type

		files = []

		# Open specific type of companion file, if specified.
		if open_file_type:
			print('\nopen file type:', open_file_type) # DEBUG
			if open_file_type == 'route_js':
				files.append(self.get_path_for_file_in('routes'))

			if open_file_type == 'controller_js':
				files.append(self.get_path_for_file_in('controllers'))

			if open_file_type == 'template_hbs':
				if app_folder == 'tests/':
					files.append(self.get_path_for_file_in('app/templates'))
					files.append(self.get_path_for_file_in('addon/templates'))
					files.append(self.get_path_for_file_in('app', 'hbs')) # co-located structure
				else:
					files.append(self.get_path_for_file_in('templates'))
					files.append(self.get_path_for_file_in('templates/components'))
					files.append(self.get_path_for_file_in('components', 'hbs')) # co-located structure

			if open_file_type == 'style':
				files += self.get_style_paths_for_file()

			if open_file_type == 'test_js':
				files += self.get_test_paths_for_file()

			if open_file_type == 'integration_test':
				files += self.get_test_paths_for_file('integration')

			if open_file_type == 'unit_test':
				files += self.get_test_paths_for_file('unit')

			if open_file_type == 'acceptance_test':
				files += self.get_test_paths_for_file('acceptance')
		# Guess the companion file to open.
		else:
			print('\nguess file type') # DEBUG
			# For a test file, open its JS companion.
			if app_folder == 'tests/':
				if file_folder in ['integration/', 'unit/']:
					files.append(self.get_path_for_file_in(app_folder))

			# For a template, open its JS companion (component, route, or controller).
			elif file_folder == 'templates/':
				# File is in `templates/components/` and we should surface the component JS file.
				if 'components/' in file_path:
					files.append('%s%s%s.js' % (app_folder_path, file_path, file_name))
				# File is in `templates/` __but not `templates/components/`__ and we should surface the
				# route and controller JS files.
				else:
					files.append(self.get_path_for_file_in('routes'))
					files.append(self.get_path_for_file_in('controllers'))

			# For a component JS file, open its template.
			elif file_folder == 'components/':
				# Use file type to determine which companion file to get, since the app could be using a
				# co-located file structure.
				if file_type == 'hbs':
					files.append(self.get_path_for_file_in('components')) # co-located structure
				else:
					files.append(self.get_path_for_file_in('templates'))
					files.append(self.get_path_for_file_in('components', 'hbs')) # co-located structure

			# For a route, open its template.
			elif file_folder == 'routes/':
				files.append(self.get_path_for_file_in('templates'))

			# For a controller, open its template.
			elif file_folder == 'controllers/':
				files.append(self.get_path_for_file_in('templates'))

		print('\nfiles possible:') # DEBUG
		[print('\t' + file) for file in files] # DEBUG

		# Filter out files that don’t exist.
		files = [file for file in files if path.exists(file)]

		print('\nfiles that exist:') # DEBUG
		[print('\t' + file) for file in files] # DEBUG

		return files


	def get_path_for_file_in(self, folder, file_type=''):
		# Remove any trailing slash from the folder name.
		folder = re.sub(r'/$', '', folder)

		if folder in ['app', 'addon']:
			file_name = re.sub(r'-test$', '', self.file_name)

			return '%s%s/%s%s.%s' % (self.app_path, folder, self.file_path, file_name, file_type or 'js')

		if folder in ['app/templates', 'addon/templates']:
			file_name = re.sub(r'-test$', '', self.file_name)

			return '%s%s/%s%s.hbs' % (self.app_path, folder, self.file_path, file_name)

		if folder.startswith('templates'):
			if self.file_folder == 'components/':
				return '%s%s/components/%s%s.hbs' % (self.app_folder_path, folder, self.file_path, self.file_name)
			return '%s%s/%s%s.hbs' % (self.app_folder_path, folder, self.file_path, self.file_name)

		return '%s%s/%s%s.%s' % (self.app_folder_path, folder, self.file_path, self.file_name, file_type or 'js')


	def get_style_paths_for_file(self):
		files = []
		# SHORTCUT: Try and use the existence of `styles/app.*` or `styles/addon.*` to determine the
		# type of style files being used.
		app_style_file_type = self.get_app_style_file_type()
		app_style_file_types = [app_style_file_type] if app_style_file_type else STYLE_FILE_TYPES

		print('\ntype:', app_style_file_type or ('%s (UNKNOWN)' % STYLE_FILE_TYPES)) # DEBUG

		if '.' + self.file_type == app_style_file_type:
			print('\nfile is a style file!') # DEBUG
			return []

		app_styles_path = self.app_folder_path + 'styles/'

		def get_file_paths_for_path(path):
			path = re.sub(r'/$', '', path)
			path_files = []
			# .../app/styles/<file_path>/<file_name>.css
			path_files += get_file_type_paths_for('%s%s/%s'        % (app_styles_path, path, self.file_name), app_style_file_types)
			# .../app/styles/<file_path>/index.css
			path_files += get_file_type_paths_for('%s%s/index'     % (app_styles_path, path),                 app_style_file_types)
			# .../app/styles/<file_path>/_index.css
			path_files += get_file_type_paths_for('%s%s/_index'    % (app_styles_path, path),                 app_style_file_types)
			# .../app/styles/<file_path>/<file_name>/index.css
			path_files += get_file_type_paths_for('%s%s/%s/index'  % (app_styles_path, path, self.file_name), app_style_file_types)
			# .../app/styles/<file_path>/<file_name>/_index.css
			path_files += get_file_type_paths_for('%s%s/%s/_index' % (app_styles_path, path, self.file_name), app_style_file_types)

			return path_files

		file_path = ''
		file_path_prefix = ''

		# Strip `components/` from the front of the file path, if necessary.
		if self.file_path.startswith('components/'):
			file_path = self.file_path.split('components/', 1)[1]
			file_path_prefix = 'components/'
		else:
			file_path = self.file_path

		# Traverse up the file path and add style-file-path options for each level.
		#
		# > NOTE: `file_path` should have a trailing slash but NO leading slash, e.g. `foo/bar/baz/`.
		while True:
			# Get style file paths for the path (but only if it exists).
			if path.exists(app_styles_path + file_path):
				print('\npath:         ', file_path) # DEBUG
				files += get_file_paths_for_path(file_path)
			else:
				print('\npath:         ', file_path, '  <-- PATH DOES NOT EXIST') # DEBUG

			# Get style file paths for the “prefixed” version of the path (but only if it exists).
			if file_path_prefix:
				if path.exists(app_styles_path + file_path_prefix + file_path):
					print('path prefixed:', file_path_prefix + file_path) # DEBUG
					files += get_file_paths_for_path(file_path_prefix + file_path)
				else:
					print('path prefixed:', file_path_prefix + file_path, '  <-- PATH DOES NOT EXIST') # DEBUG

			# If this is the top-level directory of the path.
			if file_path.count('/') is 1:
				break

			# Go up one directory.
			file_path_up_one = file_path.rsplit('/', 2)[0] + '/'

			# Safety check.
			if file_path_up_one == file_path:
				print('infinite loop prevented for file path:', file_path)
				break

			file_path = file_path_up_one

		return files


	def get_test_paths_for_file(self, test_type=None):
		should_get_integration_test = False
		should_get_unit_test        = False
		should_get_acceptance_test  = False

		# Get paths to the different test file types.
		def get_file_paths_for_path(path):
			path_files = []

			# Only try for an integration test if the file is in `components/`
			if should_get_integration_test and path.startswith('components/'):
				# .../tests/integration/<file_path>/<file_name>-test.js
				path_files.append('%stests/integration/%s%s-test.js' % (self.app_path, path, self.file_name))

			if should_get_unit_test:
				# .../tests/unit/<file_path>/<file_name>-test.js
				path_files.append('%stests/unit/%s%s-test.js' % (self.app_path, path, self.file_name))

			if should_get_acceptance_test:
				# .../tests/acceptance/<file_path>/<file_name>-test.js
				path_files.append('%stests/acceptance/%s%s-test.js' % (self.app_path, path, self.file_name))

			return path_files

		files = []

		# Determine which test files to get.
		if test_type is None:
			should_get_integration_test = True
			should_get_unit_test        = True
			should_get_acceptance_test  = True
		else:
			if test_type == 'integration':
				should_get_integration_test = True
			if test_type == 'unit':
				should_get_unit_test        = True
			if test_type == 'acceptance':
				should_get_acceptance_test  = True

		# [Shortcut] If we’re already in a test file and trying to get another test file.
		if self.file_name.endswith('-test') and self.file_type == 'js':
			if should_get_integration_test:
				if self.file_folder == 'integration/': # DEBUG
					print('\nfile is already an integration test file!') # DEBUG
				return ['%stests/integration/%s%s.js' % (self.app_path, self.file_path, self.file_name)]
			if should_get_unit_test:
				if self.file_folder == 'unit/':
					print('\nfile is already an unit test file!') # DEBUG
				return ['%stests/unit/%s%s.js' % (self.app_path, self.file_path, self.file_name)]
			if should_get_acceptance_test:
				if self.file_folder == 'acceptance/':
					print('\nfile is already an acceptance test file!') # DEBUG
				return ['%stests/acceptance/%s%s.js' % (self.app_path, self.file_path, self.file_name)]

		file_path = self.file_path

		# For templates, add test file paths prefixed with `routes/` (in case the template belongs to
		# a route).
		if self.file_folder == 'templates/':
			files += get_file_paths_for_path('routes/' + file_path)
		# For all other file types, prefix the file path with file folder (since tests will be located
		# in e.g. `tests/unit/<FILE_FOLDER>/foo-test.js`).
		else:
			file_path = self.file_folder + file_path

		print('\npath:', file_path) # DEBUG

		# Traverse up the file path and add test-file-path options for each level.
		#
		# > NOTE: `file_path` should have a trailing slash but NO leading slash, e.g. `foo/bar/baz/`.
		while True:
			files += get_file_paths_for_path(file_path)

			# If this is the top-level directory of the path.
			if file_path.count('/') <= 1:
				break

			# Go up one directory.
			file_path_up_one = file_path.rsplit('/', 2)[0] + '/'

			# Safety check.
			if file_path_up_one == file_path:
				print('infinite loop prevented for file path:', file_path)
				break

			file_path = file_path_up_one

		return files


	def get_app_style_file_type(self):
		for style_file_type in STYLE_FILE_TYPES:
			if path.exists('%sstyles/app%s' % (self.app_folder_path, style_file_type)):
				return style_file_type
			if path.exists('%sstyles/addon%s' % (self.app_folder_path, style_file_type)):
				return style_file_type

		return ''
