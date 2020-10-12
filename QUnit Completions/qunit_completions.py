import sublime
import sublime_plugin
import re



PRECEDING_INCOMPLETE_METHOD_REGEX = re.compile(r'''
    .*
    [\s\w\)]  # whitespace/letter/close-paren MUST precede `.`
    (?P<incomplete_method_text>
        \.    # `.`
        \w*   # then optionally some letters
    )
    $
''', re.X)

OPEN_GROUP_CHARS  = '({['
CLOSE_GROUP_CHARS = ')}]'
# STRING_CHARS = '"\'`'


def get_match(string, regex, group = None):
    if isinstance(regex, str):
        regex = re.compile(regex)

    match = regex.match(string)

    if match:
        if group is not None:
            return match.group(group)
        else:
            return match
    else:
        return None


def is_match(string, regex):
    return bool(get_match(string, regex, 0))


# def get_start_point(point_or_region):
#     if isinstance(point_or_region, int):
#         return point_or_region
#     else:
#         return point_or_region.begin()


def region_for(point_or_region):
    if isinstance(point_or_region, int):
        return sublime.Region(point_or_region)
    else:
        return sublime.Region(point_or_region.begin(), point_or_region.end())


def get_prev_char(view, point_or_region):
    region = region_for(point_or_region)
    return view.substr(region.begin() - 1)


# def get_prev_char_region(view, point_or_region):
#     point = get_start_point(point_or_region)
#     return sublime.Region(point - 1)


# def get_prev_char_info(view, point_or_region):
#     point = get_start_point(point_or_region)
#     region = sublime.Region(point - 1)
#
#     return {
#         substr: view.substr(region),
#         region: region,
#         scopes: view.scope_name(point)
#     }


def expand_to_scope(view, point_or_region, scope):
    """
    Given a point or a region, return a Region which encompasses the extent of the given scope.

    This is similar to `run_command('expand_selection', { to: 'scope' })`, however it is resilient
    to bugs which occur due to language files adding scopes inside the requested region.
    """

    region = region_for(point_or_region)
    start = region.begin()
    end = region.end()

    while start > 0 and view.match_selector(start - 1, scope):
        start -= 1

    while end < view.size() and view.match_selector(end, scope):
        end += 1

    return sublime.Region(start, end)


def escape(string):
    return re.sub(r'\n', '\\\\n', string)


def is_escaped(view, point):
    return get_prev_char(view, point - 1) == '\\'


def get_preceding_text(view, point_or_region):
    region = region_for(point_or_region)
    line = view.line(region)
    preceding_text_region = sublime.Region(line.begin(), region.end())
    return view.substr(preceding_text_region)


def get_preceding_text_match(view, point_or_region, regex):
    preceding_text = get_preceding_text(view, point_or_region)
    return get_match(preceding_text, regex)




class QunitCompletions(sublime_plugin.EventListener):

    def __init__(self):
        self.completions_dict = {}

        self.qunit_dom_methods_dict = {
            'exists'                        : '($1)', # options.count
            'doesNotExist'                  : '($1)',
            'isChecked'                     : '($1)',
            'isNotChecked'                  : '($1)',
            'isFocused'                     : '($1)',
            'isNotFocused'                  : '($1)',
            'isRequired'                    : '($1)',
            'isNotRequired'                 : '($1)',
            'isVisible'                     : '($1)', # options.count
            'isNotVisible'                  : '($1)',
            'hasAttribute'                  : '(${1:attributeName}, ${2:attributeValueStr/Rgx/Obj})', # name, value
            'doesNotHaveAttribute'          : '(${1:attributeName})', # name
            'hasAria'                       : '(${1:attributeNameWithoutAriaPrefix}, ${2:attributeValueStr/Rgx/Obj})', # name, value
            'doesNotHaveAria'               : '(${1:attributeNameWithoutAriaPrefix})', # name
            'hasProperty'                   : '(${1:propertyName}, ${2:propertyValueStr/Rgx})', # name, value
            'isDisabled'                    : '($1)',
            'isNotDisabled'                 : '($1)',
            'hasClass'                      : '(${1:classStr/Rgx})', # class
            'doesNotHaveClass'              : '(${1:classStr/Rgx})', # class
            'hasText'                       : '(\'${1:textStr/Rgx}\')', # text
            'hasAnyText'                    : '($1)',
            'hasNoText'                     : '($1)',
            'includesText'                  : '(\'${1:text}\')', # text
            'doesNotIncludeText'            : '(\'${1:text}\')', # text
            'hasValue'                      : '(\'${1:valueStr/Rgx/Obj}\')', # value
            'hasAnyValue'                   : '($1)',
            'hasNoValue'                    : '($1)',
            'matchesSelector'               : '(\'${1:selector}\')', # selector
            'doesNotMatchSelector'          : '(\'${1:selector}\')', # selector
            'hasTagName'                    : '(\'${1:tagName}\')', # tagName
            'doesNotHaveTagName'            : '(\'${1:tagName}\')', # tagName
            'hasStyle'                      : '({ ${1:property}: ${2:value} })', # styleObj
            'doesNotHaveStyle'              : '({ ${1:property}: ${2:value} })', # styleObj
            'hasPseudoElementStyle'         : '(\'${1:pseudoElementSelector}\', { ${2:property}: ${3:value} })', # selector, styleObj
            'doesNotHavePseudoElementStyle' : '(\'${1:pseudoElementSelector}\', { ${2:property}: ${3:value} })', # selector, styleObj
        }

        self.qunit_dom_method_aliases_dict = {
            'hasNoAttribute'            : 'doesNotHaveAttribute',
            'lacksAttribute'            : 'doesNotHaveAttribute',
            'isEnabled'                 : 'isNotDisabled',
            'hasNoClass'                : 'doesNotHaveClass',
            'lacksClass'                : 'doesNotHaveClass',
            'matchesText'               : 'hasText',
            'containsText'              : 'includesText',
            'hasTextContaining'         : 'includesText',
            'doesNotContainText'        : 'doesNotIncludeText',
            'doesNotHaveTextContaining' : 'doesNotIncludeText',
            'lacksValue'                : 'hasNoValue',
        }


    def on_query_completions(self, view, prefix, locations):
        # [Sanity Check] Only trigger within JS scopes.
        if not view.match_selector(locations[0], 'source.js'):
            return None

        print('\nQUNIT QUERY COMPLETIONS\n') # DEBUG

        if prefix == 'a':
            return ['assert\tQUnit', 'assert']

        location = locations[0]
        preceding_text = get_preceding_text(view, location)

        print(prefix, ' ', preceding_text, ' ', get_match(preceding_text, r'.*\.\w*$', 0), ' ', get_match(preceding_text, PRECEDING_INCOMPLETE_METHOD_REGEX, 0)) # DEBUG

        #preceding_incomplete_method_match = get_preceding_text_match(view, location, PRECEDING_INCOMPLETE_METHOD_REGEX)

        # Check if there’s a period (and optionally letters) preceding the current location.
        # If so, then move the start location to before the period before testing for tokens.
        if is_match(preceding_text, PRECEDING_INCOMPLETE_METHOD_REGEX):
            preceding_incomplete_method = get_match(preceding_text, PRECEDING_INCOMPLETE_METHOD_REGEX, 'incomplete_method_text')
            location = location - len(preceding_incomplete_method)
            print('  MOVE LOCATION BACK %s CHARS TO ACCOUNT FOR PRECEDING "%s"' % (len(preceding_incomplete_method), preceding_incomplete_method))
        # If there was no `prefix` then manually check to see if the preceding character
        #else


        # Determine whether to show completions

        if self.is_after_token(view, location, 'assert', 'support.module.node, variable - variable.function'):
            return self.get_qunit_completions(view, prefix, locations)

        if self.is_after_token(view, location, 'dom', 'meta.function-call variable.function', True):
            return self.get_qunit_dom_completions(view, prefix, locations)

        return None


    def is_after_token(self, view, location, token_str, selector, allow_other_tokens_matching_selector=False):
        inside_group_count = 0

        char_index = location - 1
        char = view.substr(char_index)
        open_group_chars_to_match = []

        #print('\nFIND TOKEN "%s"' % token_str) # DEBUG

        while True:
            #print(' ', char_index, char) # DEBUG
            ## indent = ' ' * (len(str(char_index)) + 2) # DEBUG
            #indent = '' # DEBUG

            open_group_char_index = OPEN_GROUP_CHARS.find(char)
            close_group_char_index = CLOSE_GROUP_CHARS.find(char)

            if open_group_char_index > -1 and not is_escaped(view, char_index):
                # If we’re not in a group but we have an open group char then quit, because we’ve
                # reached the beginning of the containing block.
                if inside_group_count == 0:
                    #print(indent, 'CHAR IS BEGINNING OF CONTAINING BLOCK') # DEBUG
                    return False
                # If we’re in a group but the open-group-char doesn’t match then there’s a syntax
                # error and we can quit.
                if char != open_group_chars_to_match[-1]:
                    #print(indent, 'CHAR DOESN’T MATCH, THERE MUST BE AN ERROR') # DEBUG
                    return False
                #print(indent, 'CHAR CLOSES GROUP', inside_group_count) # DEBUG
                inside_group_count -= 1
                open_group_chars_to_match.pop()
            elif view.match_selector(char_index, 'string, comment, regex, regexp'):
                #print(indent, 'CHAR IS PART OF STRING, COMMENT OR REGEX') # DEBUG
                ignore_region = expand_to_scope(view, char_index, 'string, comment, regex, regexp')
                char_index = ignore_region.begin()
                #print((' ' * (len(str(char_index)) + 2)), view.substr(ignore_region)) # DEBUG
                #print(indent, 'SKIP TO', char_index - 1) # DEBUG
            elif close_group_char_index > -1 and not is_escaped(view, char_index):
                open_group_chars_to_match.append(OPEN_GROUP_CHARS[close_group_char_index])
                inside_group_count += 1
                #print(indent, 'CHAR OPENS GROUP ', inside_group_count) # DEBUG
            # elif inside_group_count == 0 and escape_selector and view.match_selector(char_index, escape_selector):
            ##     print(indent, 'QUIT SINCE CHAR `%s` MATCHES ESCAPE SELECTOR' % char) # DEBUG
            #     return False
            elif inside_group_count == 0 and is_match(char, r'\w') and not view.match_selector(char_index, selector):
                #print(indent, 'QUIT SINCE CHAR `%s` IS PART OF A TOKEN THAT DOES NOT MATCH SELECTOR' % char) # DEBUG
                return False
            elif inside_group_count == 0 and view.match_selector(char_index, selector):
                #print('FOUND MATCHING SCOPE') # DEBUG
                token_region = expand_to_scope(view, char_index, selector)
                if view.substr(token_region) == token_str and inside_group_count == 0:
                    #view.sel().subtract(view.sel()[0])
                    #view.sel().add(token_region)
                    #print('FOUND `%s`!' % token_str) # DEBUG
                    return True
                if allow_other_tokens_matching_selector:
                    char_index = token_region.begin()
                    #print(indent, 'TOKEN `%s` DOES NOT MATCH ESCAPE SELECTOR' % view.substr(token_region)) # DEBUG
                    #print(indent, 'SKIP TO', char_index) # DEBUG
                else:
                    #print(indent, 'QUIT SINCE TOKEN `%s` IS NOT `%s`' % (view.substr(token_region), token_str)) # DEBUG
                    return False



            char_index -= 1
            char = view.substr(char_index)

            if char_index < 0:
                #print(indent, 'QUIT SINCE AT BEGINNING OF FILE') # DEBUG
                return False


    def get_qunit_completions(self, view, prefix, locations):
        current_index = locations[0]
        previous_chars_index = current_index - len(prefix)
        previous_1_char  = view.substr(sublime.Region(previous_chars_index - 1, previous_chars_index))

        if previous_1_char != '.':
            return None

        #print('------------------') # DEBUG
        #print('prefix:           "%s"' % escape(prefix)) # DEBUG
        #print('location[0]:      %s'   % current_index) # DEBUG
        #print('substr:           "%s"' % escape(view.substr(sublime.Region(current_index, current_index + 3)))) # DEBUG
        #print('previous_1_char:  "%s"' % escape(previous_1_char)) # DEBUG
        #print('------------------') # DEBUG

        qunit_completion_list = [
            ['async\tQUnit'          , 'async(${1:acceptCallCount=1})'],
            ['deepEqual\tQUnit'      , 'deepEqual(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['equal\tQUnit'          , 'equal(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['expect\tQUnit'         , 'expect(${1:amount})'],
            ['notDeepEqual\tQUnit'   , 'notDeepEqual(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['notEqual\tQUnit'       , 'notEqual(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['notOk\tQUnit'          , 'notOk(${1:state}${2:, \'${3:message}\'})'],
            ['notPropEqual\tQUnit'   , 'notPropEqual(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['notStrictEqual\tQUnit' , 'notStrictEqual(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['ok\tQUnit'             , 'ok(${1:state}${2:, \'${3:message}\'})'],
            ['propEqual\tQUnit'      , 'propEqual(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['pushResult\tQUnit'     , 'pushResult(${1:data = { result, actual, expected, message \\}})'],
            ['rejects\tQUnit'        , 'rejects(${1:promise}${2:, ${3:matchStr/Rgx/Err/Fn}}${4:, \'${5:message}\'})'],
            ['step\tQUnit'           , 'step(${1:message})'],
            ['strictEqual\tQUnit'    , 'strictEqual(${1:actual}, ${2:expected}${3:, \'${4:message}\'})'],
            ['throws\tQUnit'         , 'throws(${1:errorFn}${2:, ${3:errObj/ErrConstructor/Fn}}${4:, \'${5:message}\'})'],
            ['timeout\tQUnit'        , 'timeout(${1:waitMilliseconds})'],
            ['verifySteps\tQUnit'    , 'verifySteps(${1:stepsArr}${2:, \'${4:message}\'})'],
        ]

        qunit_plugin_completion_list = [
            ['dom\tQUnit DOM', 'dom(${1:elementOrSelector})$2'],
        ]

        flags = sublime.INHIBIT_EXPLICIT_COMPLETIONS

        return (qunit_completion_list + qunit_plugin_completion_list, flags)


    def get_qunit_dom_completions(self, view, prefix, locations):
        current_index = locations[0]
        previous_chars_index = current_index - len(prefix)
        previous_1_char = view.substr(sublime.Region(previous_chars_index - 1, previous_chars_index))
        next_1_char     = view.substr(sublime.Region(current_index, current_index + 1))

        if previous_1_char != '.':
            return None

        next_char_is_open_paren = next_1_char == '('

        #print('------------------') # DEBUG
        #print('prefix:           "%s"' % escape(prefix)) # DEBUG
        #print('location[0]:      %s'   % current_index) # DEBUG
        #print('substr:           "%s"' % escape(view.substr(sublime.Region(current_index, current_index + 3)))) # DEBUG
        #print('previous_1_char:  "%s"' % escape(previous_1_char)) # DEBUG
        #print('next_1_char:      "%s"' % escape(next_1_char)) # DEBUG
        #print('------------------') # DEBUG

        qunit_dom_completion_list = self.build_completion_list_for_qunit_dom_methods(view, prefix, locations, next_char_is_open_paren)

        flags = sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS

        return (qunit_dom_completion_list, flags)

    # """
    # Generate a completion list for Qunit DOM methods.
    # """
    def build_completion_list_for_qunit_dom_methods(self, view, prefix, locations, next_char_is_open_paren):
        completions_list = []

        for method, params in self.qunit_dom_methods_dict.items():
            completion = ''

            if next_char_is_open_paren:
                completion = method
            else:
                completion = ''.join([method, params])

            completions_list.append((method + '\tQUnit DOM', completion))

        for method, alias in self.qunit_dom_method_aliases_dict.items():
            completion = ''

            if next_char_is_open_paren:
                completion = method
            else:
                params = self.qunit_dom_methods_dict.get(alias)
                completion = ''.join([method, params])

            completions_list.append((method + '\tQUnit DOM (Alias)', completion))

        return completions_list

    # def on_selection_modified(self, view):
    #     # TODO: SET AUTO COMPLETE TO TRIGGER ON '.'
