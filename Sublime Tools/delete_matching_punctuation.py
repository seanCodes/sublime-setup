import sublime
import sublime_plugin
import re



BRACKET_OPEN_CHARS  = '([{'
BRACKET_CLOSE_CHARS = ')]}'

def get_char_match(char):
	open_char_index  = BRACKET_OPEN_CHARS.find(char)
	close_char_index = BRACKET_CLOSE_CHARS.find(char)
	if open_char_index >= 0:
		return BRACKET_CLOSE_CHARS[open_char_index]
	if close_char_index >= 0:
		return BRACKET_OPEN_CHARS[close_char_index]
	return None

def get_open_char_match(char):
	if char not in BRACKET_CLOSE_CHARS:
		return None
	return get_char_match(char)

def get_close_char_match(char):
	if char not in BRACKET_OPEN_CHARS:
		return None
	return get_char_match(char)


# TEST
#
# const x = [{}, { a: { b: { c: {} }, d: {} } }, { e: { f: { g: {} }, h: {} }, i: {} }, { j: {}, k: /\{/ }]
#

def split_by_char_not_in_group(str, split_char, include_empty_tokens=True):
	"""
	Split a string by instances of the given character (but only ones that are NOT enclosed in a
	group, like quotes or brackets).

	```python
	split_by_char_not_in_group('"foo," + bar(1 + "hi") + YO+"not + this" + ("here" + "hi")', '+')
	>>> ['"foo,"', 'bar(1 + "hi")', 'YO', '"not + this"', '("here" + "hi")']
	```
	"""
	out = []

	if not str:
		return out

	# The current token.
	token = ''

	# Characters that open a group.
	open_group_chars = '"\'([{'
	# Characters that close a group. (Note: The order of the characters here should match the order
	# used for `open_group_chars`.)
	close_group_chars = '"\')]}'
	string_chars = '"\''

	matching_close_group_chars = []
	inside_group = 0
	inside_string = False
	next_is_literal = False

	#for i, char in enumerate(str):
	for char in str:
		#print('char: \'' + char + '\'') # DEBUG
		if next_is_literal: # previous char was a `\`
			#print('  LITERAL') # DEBUG
			token += char
			next_is_literal = False

			continue

		if char == '\\':
			#print('  CHAR IS ESCAPE') # DEBUG
			#print('  NEXT IS LITERAL') # DEBUG
			token += char
			next_is_literal = True

			continue

		if inside_group:
			if char == matching_close_group_chars[-1]:
				#print('  CHAR CLOSES GROUP', inside_group) # DEBUG
				inside_group -= 1
				if char in string_chars:
					inside_string = False
					#print('  CHAR CLOSES STRING') # DEBUG
				token += char
				matching_close_group_chars.pop()

				continue

		elif char == split_char:
			#print('  CHAR IS SEPARATOR') # DEBUG
			if token.strip() != '' or include_empty_tokens:
				#print('  TOKEN: "' + token.strip() + '"') # DEBUG
				out.append(token.strip())
			token = ''

			continue

		token += char
		open_group_char_index = open_group_chars.find(char)

		if open_group_char_index > -1:
			if inside_string:
				#print('  SKIP OPEN GROUP CHAR (INSIDE STRING)') # DEBUG

				continue
			matching_close_group_chars.append(close_group_chars[open_group_char_index])
			inside_group += 1
			#print('  CHAR OPENS GROUP ', inside_group) # DEBUG
			if char in string_chars:
				inside_string = True
				#print('  CHAR OPENS STRING') # DEBUG

	if token.strip() != '' or include_empty_tokens:
		#print('  TOKEN: "' + token.strip() + '"') # DEBUG
		out.append(token.strip())

	#print('OUT:', out) # DEBUG
	return out

def split_by_char_not_in_quotes(str, split_char, include_empty_tokens=True):
	"""
	Split a string by un-enclosed instances of the given character (i.e. characters that are not
	inside of quotes).

	```python
	split_by_char_not_in_quotes('"foo," + bar(1 + "hi") + YO+"not + this" + ("here" + "hi")', '+')
	>>> ['"foo,"', 'bar(1 + "hi")', 'YO', '"not + this"', '("here" + "hi")']
	```
	"""
	out = []

	if not str:
		return out

	# The current token.
	token = ''

	# Characters that open a quote.
	open_quote_chars = '"\''
	# Characters that close a quote. (Note: The order of the characters here should match the order
	# used for `open_quote_chars`.)
	close_quote_chars = '"\''

	matching_close_quote_char = ''
	inside_quotes = False
	next_is_literal = False

	#for i, char in enumerate(str):
	for char in str:
		#print('char: \'' + char + '\'') # DEBUG
		if next_is_literal: # previous char was a `\`
			#print('  LITERAL') # DEBUG
			token += char
			next_is_literal = False

			continue

		if inside_quotes:
			if char == '\\':
				#print('  CHAR IS ESCAPE') # DEBUG
				#print('  NEXT IS LITERAL') # DEBUG
				token += char
				next_is_literal = True

				continue

			token += char

			if char == matching_close_quote_char:
				#print('  CHAR CLOSES QUOTE') # DEBUG
				inside_quotes = False

			continue

		if char == split_char:
			#print('  CHAR IS SEPARATOR') # DEBUG
			if token.strip() != '' or include_empty_tokens:
				#print('  TOKEN: "' + token.strip() + '"') # DEBUG
				out.append(token.strip())
			token = ''

			continue

		token += char
		quote_char_index = open_quote_chars.find(char)

		if quote_char_index > -1:
			matching_close_quote_char = close_quote_chars[quote_char_index]
			inside_quotes = True
			#print('  CHAR OPENS QUOTE') # DEBUG

	if token.strip() != '' or include_empty_tokens:
		#print('  TOKEN: "' + token.strip() + '"') # DEBUG
		out.append(token.strip())

	#print('OUT:', out) # DEBUG
	return out

def get_char_region(char_index):
	return sublime.Region(char_index, char_index + 1)



class SublimeToolsDeleteMatchingPunctuationCommand(sublime_plugin.TextCommand):


	def run(self, edit):
		#print('—————————————') # DEBUG
		exclude_scope = 'comment, string'
		view = self.view
		#new_selections = []
		#selections = []

		#print('\nSTART:\n') # DEBUG
		# # DEBUG
		#for selection in view.sel(): # DEBUG
		#	print(selection) # DEBUG
		#	#selections.append(selection) # DEBUG
		# # DEBUG
		#print('\nDO:\n') # DEBUG
		regions_to_select = []

		for selection in view.sel():
			start = selection.begin()

			# Selections must be empty or contain a single character.
			if selection.size() > 1:
				return
			# Selections must have at least one previous character.
			if start < 1:
				return

			if view.match_selector(start - 1, 'string'):
				# If we start in a string we need to stay in a string.
				exclude_scope = '- string'
			if view.match_selector(start - 1, 'comment'):
				# If we start in a comment we need to stay in a comment.
				exclude_scope = '- comment'

			char_region = get_char_region(start - 1) if selection.size() == 0 else selection
			char = view.substr(char_region)

			if char in BRACKET_OPEN_CHARS:
				matching_char_region = self.find_matching_bracket(char_region.begin(), exclude_scope)
				if matching_char_region:
					view.erase(edit, matching_char_region)
					view.erase(edit, char_region)
					# regions_to_select.append(char_region)
					# regions_to_select.append(matching_char_region)
					#regions_to_select.append(char_region.cover(matching_char_region))
				else:
					view.window().status_message('No matching character found')
			elif char in BRACKET_CLOSE_CHARS:
				matching_char_region = self.find_prev_containing_bracket(get_open_char_match(char), char_region.begin(), exclude_scope)
				if matching_char_region:
					view.erase(edit, char_region)
					view.erase(edit, matching_char_region)
					# regions_to_select.append(char_region)
					# regions_to_select.append(matching_char_region)
					#regions_to_select.append(char_region.cover(matching_char_region))
				else:
					view.window().status_message('No matching character found')
			else:
				view.window().status_message('Selection or previous character is not valid')


		view.sel().add_all(regions_to_select)

		"""
			#print(selection) # DEBUG
			object_start_index = self.find_prev_containing_bracket('{', selection.begin(), EXCLUDE_SCOPE)

			# DEBUG
			#print('start index', object_start_index) # DEBUG
			#view.sel.add(sublime.Region(object_start_index, object_start_index + 1))
			#return

			if object_start_index == -1:
				continue

			object_end_index = self.find_matching_bracket(object_start_index, EXCLUDE_SCOPE)
			object_region = sublime.Region(object_start_index + 1, object_end_index - 1)
			#print(view.substr(object_region)) # DEBUG

			key_value_pairs = []
			out = ''

			if collapse:
				key_value_pairs = split_by_char_not_in_quotes(view.substr(object_region), '\n', False)

				if len(key_value_pairs):
					out = ' %s ' % ' '.join(key_value_pairs)
					# Clean up any trailing commas.
					out = re.sub(r', (}|$)', r' \1', out)

				#key_value_pairs = split_by_char_not_in_quotes(view.substr(object_region), ',', False)
				#if len(key_value_pairs):
				#	out = ' %s ' % ', '.join(key_value_pairs)
				#	# Clean up any remaining whitespace.
				#	out = re.sub(r'\n\t+', ' ', out)
				#	# Clean up any trailing commas.
				#	out = re.sub(r', }', ' }', out)

				out = '{' + out + '}'
			else: # expand
				key_value_pairs = split_by_char_not_in_group(view.substr(object_region), ',', False)

				#print(key_value_pairs) # DEBUG

				if len(key_value_pairs):
					out = '%s,' % ',\n'.join(key_value_pairs)
					# TODO: Handle all indentation (not just tabs)!
					#out = out.replace('\n', '\n\t')
				else:
					view.run_command('insert_snippet', { 'contents': '\n' })
					return

			# Double-escape because the `insert_snippet` command un-escapes.
			out = out.replace('\\', '\\\\')
			# Add surrounding brackets
			#out = '{' + out + '}'

			object_region_with_brackets = sublime.Region(object_region.begin() - 1, object_region.end() + 1)

			#print(out) # DEBUG
			view.sel().add(object_region_with_brackets)
			if expand:
				view.run_command('insert_snippet', { 'contents': '{\n\t$0\n}' })
			view.run_command('insert_snippet', { 'contents': out })
			if expand:
				view.sel().subtract(object_region_with_brackets)
				view.sel().add(sublime.Region(object_region_with_brackets.end(), object_region_with_brackets.end()))
		"""


	def find_prev_containing_bracket(self, bracket, start_point, exclude_scope):
		if start_point <= 0:
			return None

		bracket_close = get_close_char_match(bracket)

		if not bracket_close:
			return None

		line = self.view.line(start_point)
		line = sublime.Region(line.begin(), start_point)
		search_str = self.view.substr(line)
		depth = 0

		while True:
			#print('search: "%s"' % search_str) # DEBUG
			line_start_index = line.begin()
			bracket_open_index  = search_str.rfind(bracket)
			bracket_close_index = search_str.rfind(bracket_close)
			has_open_bracket  = bracket_open_index  != -1 and exclude_scope and not self.view.match_selector(line_start_index + bracket_open_index,  exclude_scope)
			has_close_bracket = bracket_close_index != -1 and exclude_scope and not self.view.match_selector(line_start_index + bracket_close_index, exclude_scope)
			open_bracket_comes_first = bracket_open_index > bracket_close_index
			trim_index = 0

			if has_open_bracket and open_bracket_comes_first: # `{` OR `} {`
				#print('  - HAS OPEN %s' % bracket) # DEBUG

				if not depth:
					#print('  - FOUND') # DEBUG
					return get_char_region(line_start_index + bracket_open_index) # FOUND

				depth -= 1
				#print('  - depth-- ', depth) # DEBUG
				trim_index = bracket_open_index
			elif has_close_bracket: # }
				#print('  - HAS CLOSE %s' % bracket_close) # DEBUG

				depth += 1
				#print('  - depth++ ', depth) # DEBUG
				trim_index = bracket_close_index

			if trim_index:
				#print('  - TRIM STRING') # DEBUG
				search_str = search_str[:trim_index]
				continue

			no_more_lines = line_start_index == 0

			if no_more_lines:
				#print('  - NO MORE LINES') # DEBUG
				return None # NOT FOUND

			line = self.view.full_line(line_start_index - 1)
			search_str = self.view.substr(line)


	def find_matching_bracket(self, point, exclude_scope):
		if point < 0:
			return None

		bracket = self.view.substr(point)
		bracket_match = get_close_char_match(bracket)
		#print('BRACKET       %s' % bracket) # DEBUG
		#print('BRACKET MATCH %s' % bracket_match) # DEBUG

		if not bracket_match:
			return None

		view_size = self.view.size()
		bracket_count = 1

		while bracket_count and point < view_size:
			point += 1
			point_str = self.view.substr(point)
			if point_str == bracket_match and not self.view.match_selector(point, exclude_scope):
				bracket_count -= 1
				#print('  brackets: %s -%s' % (bracket_count, point_str)) # DEBUG
			if point_str == bracket       and not self.view.match_selector(point, exclude_scope):
				bracket_count += 1
				#print('  brackets: %s +%s' % (bracket_count, point_str)) # DEBUG

		#print('') # DEBUG

		if point == view_size:
			return None

		return get_char_region(point)
