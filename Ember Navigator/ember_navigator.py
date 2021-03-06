import sublime
import sublime_plugin
import re
from os import path



FILE_PATH_REGEX = re.compile(r'^(?P<app_folder_path>(?P<app_path>.*?/)(?P<app_folder>app/|tests/))(?P<file_folder>[^/]+/)(?P<file_path>.*?(?=[^/]+$))(?P<file_name>[^.]+)\.(?P<file_type>.*)$')
STYLE_FILE_TYPES = ['.css', '.less', '.scss', '.sass', '.styl']



class EmberNavigatorCommand(sublime_plugin.WindowCommand):


	def run(self, open_file_type='', new_tab=False):
		if not self.window.active_view().file_name():
			return sublime.status_message('File is not yet saved!')

		# Process File

		self.process_file()

		if not self.file_path_match:
			return sublime.status_message('File is not in an ember project app/*/ or tests/*/ directory!')

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

		if open_file_type:
			if open_file_type == 'route_js':
				files.append(self.get_path_for_file_in('routes'))

			if open_file_type == 'controller_js':
				files.append(self.get_path_for_file_in('controllers'))

			if open_file_type == 'template_hbs':
				if app_folder == 'tests/':
					files.append(self.get_path_for_file_in('app/templates'))
				else:
					files.append(self.get_path_for_file_in('templates'))

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
		else:
			if app_folder == 'tests/':
				if file_folder in ['integration/', 'unit/']:
					files.append(self.get_path_for_file_in('app'))

			elif file_folder == 'templates/':
				if 'components/' in file_path:
					# File is in `templates/components/` and we should surface the component js file.
					files.append('%s%s%s.js' % (app_folder_path, file_path, file_name))
				else:
					# File is in `templates/` __but not `templates/components/`__ and we should surface the
					# route and controller js files.
					files.append(self.get_path_for_file_in('routes'))
					files.append(self.get_path_for_file_in('controllers'))

			elif file_folder == 'components/':
				files.append(self.get_path_for_file_in('templates'))

			elif file_folder == 'routes/':
				files.append(self.get_path_for_file_in('templates'))

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
		if folder == 'app':
			file_name = re.sub(r'-test$', '', self.file_name)

			return '%sapp/%s%s.js' % (self.app_path, self.file_path, file_name)
		elif folder == 'app/templates':
			file_name = re.sub(r'-test$', '', self.file_name)

			return '%sapp/templates/%s%s.hbs' % (self.app_path, self.file_path, file_name)
		elif folder == 'templates':
			if self.file_folder == 'components/':
				return '%s%s/components/%s%s.hbs' % (self.app_folder_path, folder, self.file_path, self.file_name)
			else:
				return '%s%s/%s%s.hbs' % (self.app_folder_path, folder, self.file_path, self.file_name)
		else:
			return '%s%s/%s%s.js' % (self.app_folder_path, folder, self.file_path, self.file_name)


	def get_style_paths_for_file(self):
		files = []
		# SHORTCUT: Try and use the existence of `styles/app.*` to determine style files’ file-type.
		app_style_file_type = self.get_app_style_file_type()

		if '.' + self.file_type == app_style_file_type:
			print('\nfile is a style file!') # DEBUG
			return []

		def get_file_type_paths_for(path):
			if app_style_file_type:
				return [path + app_style_file_type]
			return [path + type for type in STYLE_FILE_TYPES]

		def get_file_paths_for_path(path):
			path_files = []
			# .../app/styles/<file_path>/<file_name>.css
			path_files += get_file_type_paths_for('%sstyles/%s%s' % (self.app_folder_path, path, self.file_name))
			# .../app/styles/<file_path>/<file_name>/index.css
			path_files += get_file_type_paths_for('%sstyles/%s%s/index' % (self.app_folder_path, path, self.file_name))
			# .../app/styles/<file_path>/<file_name>/_index.css
			path_files += get_file_type_paths_for('%sstyles/%s%s/_index' % (self.app_folder_path, path, self.file_name))
			# .../app/styles/<file_path>/index.css
			path_files += get_file_type_paths_for('%sstyles/%sindex' % (self.app_folder_path, path))
			# .../app/styles/<file_path>/_index.css
			path_files += get_file_type_paths_for('%sstyles/%s_index' % (self.app_folder_path, path))

			return path_files

		file_path = self.file_path

		# Strip `components/` from the front of the file path, if necessary.
		if file_path.startswith('components/'):
			file_path = file_path.split('components/', 1)[1]

		print('\npath:', file_path) # DEBUG
		print('type:', app_style_file_type or file_types) # DEBUG

		# Traverse up the file path and add style-file-path options for each level.
		#
		# > NOTE: `file_path` should have a trailing slash but NO leading slash, e.g. `foo/bar/baz/`.
		while True:
			files += get_file_paths_for_path(file_path)

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

		return ''
