import sublime
import sublime_plugin
import re



BRACKET_PAIRS = {
	'(': ')',
	'[': ']',
	'{': '}',
}

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
		#print('char: \'' + char + '\'')
		if next_is_literal: # previous char was a `\`
			#print('  LITERAL')
			token += char
			next_is_literal = False

			continue

		if char == '\\':
			#print('  CHAR IS ESCAPE')
			#print('  NEXT IS LITERAL')
			token += char
			next_is_literal = True

			continue

		if inside_group:
			if char == matching_close_group_chars[-1]:
				#print('  CHAR CLOSES GROUP', inside_group)
				inside_group -= 1
				if char in string_chars:
					inside_string = False
					#print('  CHAR CLOSES STRING')
				token += char
				matching_close_group_chars.pop()

				continue

		elif char == split_char:
			#print('  CHAR IS SEPARATOR')
			if token.strip() != '' or include_empty_tokens:
				#print('  TOKEN: "' + token.strip() + '"')
				out.append(token.strip())
			token = ''

			continue

		token += char
		open_group_char_index = open_group_chars.find(char)

		if open_group_char_index > -1:
			if inside_string:
				#print('  SKIP OPEN GROUP CHAR (INSIDE STRING)')

				continue
			matching_close_group_chars.append(close_group_chars[open_group_char_index])
			inside_group += 1
			#print('  CHAR OPENS GROUP ', inside_group)
			if char in string_chars:
				inside_string = True
				#print('  CHAR OPENS STRING')

	if token.strip() != '' or include_empty_tokens:
		#print('  TOKEN: "' + token.strip() + '"')
		out.append(token.strip())

	#print('OUT:', out)
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
		#print('char: \'' + char + '\'')
		if next_is_literal: # previous char was a `\`
			#print('  LITERAL')
			token += char
			next_is_literal = False

			continue

		if inside_quotes:
			if char == '\\':
				#print('  CHAR IS ESCAPE')
				#print('  NEXT IS LITERAL')
				token += char
				next_is_literal = True

				continue

			token += char

			if char == matching_close_quote_char:
				#print('  CHAR CLOSES QUOTE')
				inside_quotes = False

			continue

		if char == split_char:
			#print('  CHAR IS SEPARATOR')
			if token.strip() != '' or include_empty_tokens:
				#print('  TOKEN: "' + token.strip() + '"')
				out.append(token.strip())
			token = ''

			continue

		token += char
		quote_char_index = open_quote_chars.find(char)

		if quote_char_index > -1:
			matching_close_quote_char = close_quote_chars[quote_char_index]
			inside_quotes = True
			#print('  CHAR OPENS QUOTE')

	if token.strip() != '' or include_empty_tokens:
		#print('  TOKEN: "' + token.strip() + '"')
		out.append(token.strip())

	#print('OUT:', out)
	return out

#def char_region(char_index):
#	return sublime.Region(char_index, char_index + 1)

#def get_indent(view_or_text, point_or_region):
#	text = view_or_text
#
#	# If view, extract text.
#	if isinstance(view_or_text, sublime.View):
#		view = view_or_text
#
#		# If point, convert to region.
#		if isinstance(point_or_region, int):
#			point_or_region = view.line(point_or_region)
#
#		text = veiw.substr(point_or_region)
#
#	match = re.match(r'^[ \t]+', text)
#	indent = '' # TODO
#
#	return match if match is not None else ''



class Es6ObjectMultilineCommand(sublime_plugin.TextCommand):


	def run(self, edit, collapse=False):
		#print('—————————————')
		EXCLUDE_SCOPE = 'comment, string'
		view = self.view
		expand = not collapse
		#new_selections = []
		#selections = []

		# DEBUG
		#print('\nSTART:\n')
		#
		#for selection in view.sel():
		#	print(selection)
		#	#selections.append(selection)
		#
		#print('\nDO:\n')

		for selection in view.sel():
			if not view.match_selector(selection.begin(), 'source.js'):
				sublime.status_message('View is not JS')
				continue

			#print(selection)
			object_start_index = self.find_prev_containing_bracket('{', selection.begin(), EXCLUDE_SCOPE)

			# DEBUG
			#print('start index', object_start_index)
			#view.sel.add(sublime.Region(object_start_index, object_start_index + 1))
			#return

			if object_start_index == -1:
				continue

			object_end_index = self.find_matching_bracket(object_start_index, EXCLUDE_SCOPE)
			object_region = sublime.Region(object_start_index + 1, object_end_index - 1)
			#print(view.substr(object_region))

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

				out = '{%s}' % out
			else: # expand
				key_value_pairs = split_by_char_not_in_group(view.substr(object_region), ',', False)

				#print(key_value_pairs)

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

			#print(out)
			view.sel().add(object_region_with_brackets)
			if expand:
				view.run_command('insert_snippet', { 'contents': '{\n\t$0\n}' })
			view.run_command('insert_snippet', { 'contents': out })
			if expand:
				view.sel().subtract(object_region_with_brackets)
				view.sel().add(sublime.Region(object_region_with_brackets.end(), object_region_with_brackets.end()))

	# def find_prev_char(self, char, start_point, exclude_scope):
	# 	if start_point <= 0:
	# 		return -1
	#
	# 	line = self.view.line(start_point)
	# 	line = sublime.Region(line.a, start_point)
	#
	# 	while True:
	# 		match_index = self.view.substr(line).rfind(char)
	# 		line_start = line.a
	#
	# 		if match_index >= 0:
	# 			match_index += line_start
	#
	# 			if not self.view.match_selector(match_index, exclude_scope):
	# 				return match_index
	#
	# 		if line_start == 0:
	# 			return -1
	#
	# 		line = self.view.full_line(line_start - 1)


	# def find_closest_prev_bracket(self, start_point, exclude_scope):
	# 	if start_point <= 0:
	# 		return -1
	#
	# 	line = self.view.line(start_point)
	# 	line = sublime.Region(line.begin(), start_point)
	# 	search_str = self.view.substr(line)
	# 	depth = 0
	#
	# 	# ({}, [], '')
	# 	while True:
	# 		line_start_index = line.begin()
	# 		closest_bracket_open_index  = [match.start() for match in re.finditer(r'{|\[|\(', search_str)][-1]
	# 		closest_bracket_close_index = [match.start() for match in re.finditer(r'}|]|\)',  search_str)][-1]
	# 		has_open_bracket  = closest_bracket_open_index  != -1 and exclude_scope and not self.view.match_selector(line_start_index + bracket_open_index,  exclude_scope)
	# 		has_close_bracket = closest_bracket_close_index != -1 and exclude_scope and not self.view.match_selector(line_start_index + bracket_close_index, exclude_scope)
	# 		open_bracket_is_closest = bracket_open_index > bracket_close_index
	# 		trim_index = 0
	#
	# 		if has_open_bracket and open_bracket_is_closest: # `{` OR `} {`
	# 			#print('  - HAS OPEN {')
	#
	# 			if not depth:
	# 				#print('  - FOUND')
	# 				return line_start_index + bracket_open_index # FOUND
	#
	# 			depth -= 1
	# 			#print('  - depth-- ', depth)
	# 			trim_index = bracket_open_index
	# 		elif has_close_bracket: # }
	# 			#print('  - HAS CLOSE }')
	#
	# 			#
	# 			# COULD USE `find_prev_containing_bracket` HERE
	# 			#
	#
	# 			depth += 1
	# 			#print('  - depth++ ', depth)
	# 			trim_index = bracket_close_index
	#
	# 		if trim_index:
	# 			#print('  - TRIM STRING')
	# 			search_str = search_str[:trim_index]
	# 			continue
	#
	# 		no_more_lines = line_start_index == 0
	#
	# 		if no_more_lines:
	# 			#print('  - NO MORE LINES')
	# 			return -1 # NOT FOUND
	#
	# 		line = self.view.full_line(line_start_index - 1)
	# 		search_str = self.view.substr(line)


	def find_prev_containing_bracket(self, bracket, start_point, exclude_scope):
		if start_point <= 0:
			return -1

		bracket_close = BRACKET_PAIRS.get(bracket, '')

		if not bracket_close:
			return -1

		line = self.view.line(start_point)
		line = sublime.Region(line.begin(), start_point)
		search_str = self.view.substr(line)
		depth = 0

		while True:
			#print('search: "' + search_str + '"')
			line_start_index = line.begin()
			bracket_open_index  = search_str.rfind(bracket)
			bracket_close_index = search_str.rfind(bracket_close)
			has_open_bracket  = bracket_open_index  != -1 and exclude_scope and not self.view.match_selector(line_start_index + bracket_open_index,  exclude_scope)
			has_close_bracket = bracket_close_index != -1 and exclude_scope and not self.view.match_selector(line_start_index + bracket_close_index, exclude_scope)
			open_bracket_comes_first = bracket_open_index > bracket_close_index
			trim_index = 0

			if has_open_bracket and open_bracket_comes_first: # `{` OR `} {`
				#print('  - HAS OPEN {')

				if not depth:
					#print('  - FOUND')
					return line_start_index + bracket_open_index # FOUND

				depth -= 1
				#print('  - depth-- ', depth)
				trim_index = bracket_open_index
			elif has_close_bracket: # }
				#print('  - HAS CLOSE }')

				depth += 1
				#print('  - depth++ ', depth)
				trim_index = bracket_close_index

			if trim_index:
				#print('  - TRIM STRING')
				search_str = search_str[:trim_index]
				continue

			no_more_lines = line_start_index == 0

			if no_more_lines:
				#print('  - NO MORE LINES')
				return -1 # NOT FOUND

			line = self.view.full_line(line_start_index - 1)
			search_str = self.view.substr(line)

		# while True:
		# 	match_index = self.view.substr(line).rfind(bracket)
		# 	opposite_match_index = self.view.substr(line).rfind(bracket_close)
		# 	line_start = line.a
		#
		# 	if match_index && opposite_match_index:
		# 		if opposite_match_index > match_index:
		# 			depth += 1
		#
		# 	if match_index >= 0:
		# 		match_index += line_start
		#
		# 		if not self.view.match_selector(match_index, exclude_scope):
		# 			return match_index
		#
		# 	if line_start == 0:
		# 		return -1
		#
		# 	line = self.view.full_line(line_start - 1)


	def find_matching_bracket(self, point, exclude_scope):
		if point == -1:
			return -1

		bracket = self.view.substr(point)
		bracket_match = BRACKET_PAIRS.get(bracket, '')

		if not bracket_match:
			return -1

		view_size = self.view.size()
		bracket_count = 1

		while bracket_count and point < view_size:
			point += 1
			point_str = self.view.substr(point)
			if point_str == bracket_match and not self.view.match_selector(point, exclude_scope):
				bracket_count -= 1
				#print('  brackets: ' + str(bracket_count) + ' -' + point_str)
			if point_str == bracket       and not self.view.match_selector(point, exclude_scope):
				bracket_count += 1
				#print('  brackets: ' + str(bracket_count) + ' +' + point_str)

		#print('')

		if point == view_size:
			return -1

		return point + 1
