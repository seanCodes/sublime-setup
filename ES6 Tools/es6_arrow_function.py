import sublime
import sublime_plugin
import re



def split_by_char(str, split_char):
	"""
	Split a string by unenclosed instances of the given character (i.e. characters that are not
	inside of quotes or brackets).

	```python
	split_by_char('"foo," + bar(1 + "hi") + YO+"not + this" + ("here" + "hi")', '+')
	>>> ['"foo,"', 'bar(1 + "hi")', 'YO', '"not + this"', '("here" + "hi")']
	```
	"""
	out = []

	if not str:
		return out

	# The current token.
	token = ''

	# Characters that open a group. (Plus signs will not be considered string concat operators
	# when inside a group.)
	open_group_chars = '"\'<({'
	# Characters that close a group. (Note: The order of the characters here should match the order
	# used for `open_group_chars`.)
	close_group_chars = '"\'>)}'

	matching_quote = ''
	inside_quotes = False
	next_is_literal = False

	#length = len(str)

	#for i, char in enumerate(str):
	for char in str:
		#print('char: "' + char + '"')
		if next_is_literal: # previous char was a `\`
			#print('  NEXT IS LITERAL')
			token += char
			next_is_literal = False

			continue

		if inside_quotes:
			#print('  INSIDE QUOTES')
			if char == '\\':
				#print('  CHAR IS ESCAPE')
				token += char
				next_is_literal = True

				continue

			token += char

			if char == matching_quote:
				#print('  CHAR IS MATCHING CLOSE QUOTE')
				inside_quotes = False

			continue

		if char == split_char:
			#print('  CHAR IS +')
			out.append(token.strip())
			token = ''

			continue

		token += char
		quote_index = open_group_chars.find(char)

		if quote_index > -1:
			matching_quote = close_group_chars[quote_index]
			inside_quotes = True

	out.append(token.strip())

	return out



class Es6ArrowFunctionCommand(sublime_plugin.TextCommand):


	def run(self, edit):
		EXCLUDE_SCOPE = 'comment, string'
		view = self.view

		if not view.match_selector(0, 'source.js'):
			return

		for selection in view.sel():
			function_keyword_region = self.find_previous_word('function', selection.begin(), EXCLUDE_SCOPE)
			start_point = function_keyword_region.begin()

			if function_keyword_region.end() == -1:
				continue

			# Parameters

			parameters_start_point = self.find_next_char('(', start_point, EXCLUDE_SCOPE)
			parameters_end_point   = self.find_matching_bracket(parameters_start_point, EXCLUDE_SCOPE)

			if parameters_start_point == -1 or parameters_end_point == -1:
				continue

			parameters_inner_text = view.substr(sublime.Region(parameters_start_point + 1, parameters_end_point - 1))
			parameters_count = len(split_by_char(parameters_inner_text, ','))

			# Function Body

			function_body_start_point = self.find_next_char('{', parameters_end_point, EXCLUDE_SCOPE)
			function_body_end_point   = self.find_matching_bracket(function_body_start_point, EXCLUDE_SCOPE)

			if function_body_start_point == -1 or function_body_end_point == -1:
				continue

			function_body_region = sublime.Region(function_body_start_point, function_body_end_point)
			function_body_text = view.substr(function_body_region)

			if function_body_text.count('\n') <= 2:
				function_body_text = re.sub(r'^\{\s+(return )?|\s+\}$', '', function_body_text)

			function_region  = sublime.Region(start_point, function_body_end_point)
			function_keyword = sublime.Region(start_point, parameters_start_point)

			# Strip `.bind(this)`

			bind_region = view.find(r'}\s*\.bind\s*\(\s*this\s*\)', function_body_end_point - 1)

			if bind_region.begin() == function_body_end_point - 1:
				print('yes')
				view.replace(edit, bind_region, '}')

			# Assemble

			if parameters_count == 1:
				text = parameters_inner_text + ' => ' + function_body_text
			else:
				parameters_region = sublime.Region(parameters_start_point, parameters_end_point)
				text = view.substr(parameters_region) + ' => ' + function_body_text

			view.replace(edit, function_region, text)


	def find_previous_word(self, find_word, start_point, exclude_scope):
		view = self.view
		word_region = view.word(view.find_by_class(start_point, False, sublime.CLASS_WORD_START))

		while word_region.begin() != 0:
			word_region = view.word(view.find_by_class(word_region.begin(), False, sublime.CLASS_WORD_START))

			if view.substr(word_region) == find_word and not view.match_selector(word_region.begin(), exclude_scope):
				return word_region

		return sublime.Region(-1, -1)


	def find_next_char(self, char, start_point, exclude_scope):
		if start_point == -1:
			return -1

		start_region = self.view.find(char, start_point, sublime.LITERAL)

		while self.view.match_selector(start_region.begin(), exclude_scope) and start_region.begin() != -1:
			start_region = self.view.find(char, start_region.end(), sublime.LITERAL)

		return start_region.begin()


	def find_matching_bracket(self, point, exclude_scope):
		if point == -1:
			return -1

		bracket = self.view.substr(point)
		bracket_match = ''

		if bracket == '(':
			bracket_match = ')'
		if bracket == '[':
			bracket_match = ']'
		if bracket == '{':
			bracket_match = '}'

		if bracket_match == '':
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
