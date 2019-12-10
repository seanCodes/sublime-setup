import sublime
import sublime_plugin
import re



def split_by_plus_signs(str):
	"""
	Split a string by unenclosed plus signs (i.e. commas which are not inside of quotes or brackets).

	```python
	split_by_plus_signs('"foo," + bar(1 + "hi") + YO+"not + this" + ("here" + "hi")')
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

	length = len(str)

	for i, char in enumerate(str):
		#print('char: "' + char + '"')
		if next_is_literal: # previous char was a `\` or was part of `++`
			#print('  NEXT IS LITERAL')
			token += char
			next_is_literal = False

			continue

		if inside_quotes:
			#print('  INSIDE QUOTES')
			if char == '\\':
				#print('  CHAR IS ESCAPE')

				if i != length - 1 and str[i + 1] == '\n':
					#print('    CHAR IS PART OF \\\\n')
					continue

				token += char
				next_is_literal = True

				continue

			if char == '`':
				#print('  CHAR IS `')
				token += '\\'

			token += char

			if char == matching_quote:
				#print('  CHAR IS MATCHING CLOSE QUOTE')
				inside_quotes = False

			continue

		if char == '+':
			#print('  CHAR IS +')
			if i != length - 1 and str[i + 1] == '+': # screen for `++` operators
				#print('    CHAR IS PART OF ++')
				token += char
				next_is_literal = True # add the next char (the second `+`) as-is

				continue

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


def list_to_template_string(list):
	out = '`'

	for token in list:
		# Strip quote marks and append raw string.
		if token[0] == '\'' and token[-1] == '\'':
			out += token[1:-1]

			continue

		out += '${' + token + '}'

	return out + '`'


def expand_to_scope(view, pointOrRegion, scope):
	"""
	Given a point or a region, return a Region which encompasses the extent of the given scope.

	This is similar to `run_command('expand_selection', { to: 'scope' })`, however it is resilient
	to bugs which occur due to language files adding scopes inside the requested region.
	"""
	start = end = 0

	if isinstance(pointOrRegion, int):
		start = end = pointOrRegion
	else:
		start = pointOrRegion.begin()
		end = pointOrRegion.end()

	while start > 0 and view.scope_name(start - 1).find(scope) > -1:
		start -= 1

	while end < view.size() and view.scope_name(end).find(scope) > -1:
		end += 1

	return sublime.Region(start, end)



class Es6TemplateStringCommand(sublime_plugin.TextCommand):


	def run(self, edit):
		view = self.view

		for selection in view.sel():

			# If there’s a selection, convert the text under the selection to a template string.
			if not selection.empty():
				self.convert_selection_to_template_string(edit, selection)

				continue

			if view.match_selector(selection.begin(), 'string.quoted'):
				self.convert_string_to_template_string(edit, selection)


	def convert_selection_to_template_string(self, edit, region):
		view = self.view
		text = view.substr(region)
		text_as_template_string = list_to_template_string(split_by_plus_signs(text))

		view.replace(edit, region, text_as_template_string)


	def convert_string_to_template_string(self, edit, region):
		view = self.view
		point = region.begin()
		scope_region = expand_to_scope(view, point, 'string.quoted')
		text = view.substr(scope_region)
		text = re.sub(r'(?<!\\)`', '\\`', text)
		text = re.sub(r'\\\n', '\n', text)

		view.replace(edit, scope_region, '`' + text[1:-1] + '`')
