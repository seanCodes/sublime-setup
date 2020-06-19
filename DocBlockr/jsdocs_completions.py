import sublime, sublime_plugin
import re



HAS_DOC_START_REGEX = re.compile(r'^.*?/\*\*')
HAS_DOC_END_REGEX   = re.compile(r'^.*?\*/')
HAS_TAG_REGEX = re.compile(r'^\s*\*?\s*@\S+')
# “type” in the regex below must support the following scenarios (all case-insensitive):
# - `{*}`
# - `{foo}`
# - `{?foo}`
# - `{!foo}`
# - `{...foo}`
# - `{foo=}` – Closure Compiler
# - `{foo[]}`
# - `{foo.bar}`
# - `{foo.<bar>}` – Closure Compiler
# - `{foo.<bar, baz>}` – Closure Compiler
# - `{foo|bar}` – old syntax
# - `{(foo|bar)}`
# - `{{a: foo, b: bar}}` – Closure Compiler
# More strict version:
#tag_regex = re.compile(r'(?P<tag>@\w+\!?)(?:(?P<type_spaces> +?)(?P<type>\{(?:\?|!|\.\.\.)?[\w\*\.,<>()\[\]\{\}| ]+=?\}(?=\s*$| +[\w\[])))?(?:(?P<description_1_spaces> +)(?P<description_1>\S+))?(?:(?P<description_2_spaces> +)(?P<description_2>[^*{].*))?')
# This is a more loose version:
TAG_PARTS_REGEX = re.compile(r'(?P<tag>@\w+\!?)(?:(?P<type_spaces> +)(?P<type>\{.*?\}(?= +[\w\[]|\s*$)))?(?:(?P<description_1_spaces> +)(?P<description_1>\S+))?(?:(?P<description_2_spaces> +)(?P<description_2>[^*{].*))?')

def is_match(str, regex):
    match = regex.match(str)

    if match:
        return match.group(0)
    else:
        return None

def region_is_first(view, region):
    return region.begin() <= 0

def region_is_last(view, region):
    return region.end() >= view.size()

def region_has_doc_start(view, region):
    return is_match(view.substr(region), HAS_DOC_START_REGEX)

def region_has_doc_end(view, region):
    return is_match(view.substr(region), HAS_DOC_END_REGEX)

def region_has_tag(view, region):
    return is_match(view.substr(region), HAS_TAG_REGEX)

def get_tag_match(view, region):
    return TAG_PARTS_REGEX.search(view.substr(region))

# Get the line above the current region.
#
# > NOTE: This does no checking to determine if there even is a previous line!
def get_prev_line(view, region):
    return view.line(region.begin() - 1)

# Get the line below the current region.
#
# > NOTE: This does no checking to determine if there even is a previous line!
def get_next_line(view, region):
    return view.line(region.end() + 1)



class JSDocsTagCompletions(sublime_plugin.EventListener):

    # """
    # Provide tag completions for JSDocs. The completion matches just after typing a tag’s `@`.
    # """
    def __init__(self):
        self.completion_dict_for_tags = {
            # JSDoc tags as of v3.5.5
            #
            # FIELD:              Tag                 Type                   Name                         Description
            '@abstract'        : ['@abstract'],
            '@access'          : ['@access',                                 '${1:package|private|protected|public}'],
            '@alias'           : ['@alias',                                  '${1:namepath}'],
            '@arg'             : ['@arg',             '{${1:Type}}',         '${2:name}',                 '${3:Description.}'],
            '@argument'        : ['@argument',        '{${1:Type}}',         '${2:name}',                 '${3:Description.}'],
            '@async'           : ['@async'],
            '@augments'        : ['@augments',                               '${1:namepath}'],
            '@author'          : ['@author',                                 '${1:Author Name}',          '${3:<${2:optional email address}>}'],
            '@borrows'         : ['@borrows',                                '${1:other namepath}', 'as', '${2:this namepath}'],
            '@callback'        : ['@callback',                               '${1:namepath}'],
            '@class'           : ['@class',           '{${1:OptionalType}}', '${2:OptionalName}'],
            '@classdesc'       : ['@classdesc',                                                           '${1:Description.}'],
            '@const'           : ['@const',           '{${1:OptionalType}}'], # name is allowed but seems very uncommon
            '@constant'        : ['@constant',        '{${1:OptionalType}}'], # name is allowed but seems very uncommon
            '@constructor'     : ['@constructor',     '{${1:OptionalType}}', '${2:OptionalName}'],
            '@constructs'      : ['@constructs',                             '${1:Class (required if not using @lends)}'],
            '@copyright'       : ['@copyright',                                                           '${1:Info}'],
            '@default'         : ['@default',                                '${1:default value (optional unless symbol is an object or function)}'],
            '@defaultvalue'    : ['@defaultvalue',                           '${1:default value (optional unless symbol is an object or function)}'],
            '@deprecated'      : ['@deprecated',                                                          '${1:Optional description.}'],
            '@desc'            : ['@desc',                                                                '${1:Description (if description is not at top of tag).}'],
            '@description'     : ['@description',                                                         '${1:Description (if description is not at top of tag).}'],
            '@emits'           : ['@emits',                                  '${1:Class}#${2:event}'],
            '@enum'            : ['@enum',            '{${1:PropertiesType}}'],
            '@event'           : ['@event',                                  '${1:Class}#${2:event}'],
            '@example'         : ['@example',                                                             '${2:<caption>${1:Optional caption.}</caption>}\n* ${3:// example code}'],
            '@exception'       : ['@exception',       '{${1:Type}}',                                      '${2:Description.}'],
            '@exports'         : ['@exports',                                '${1:moduleName}'],
            '@extends'         : ['@extends',                                '${1:namepath}'],
            '@external'        : ['@external',                               '${1:ExternalModuleName}'],
            '@file'            : ['@file',                                                                '${1:Optional description.}'],
            '@fileoverview'    : ['@fileoverview',                                                        '${1:Optional description.}'],
            '@fires'           : ['@fires',                                  '${1:Class}#${2:event}'],
            '@func'            : ['@func',                                   '${1:optionalFunctionName}'],
            '@function'        : ['@function',                               '${1:optionalFunctionName}'],
            '@generator'       : ['@generator'],
            '@global'          : ['@global'],
            '@hideconstructor' : ['@hideconstructor'],
            '@host'            : ['@host',                                   '${1:ExternalModuleName}'],
            '@ignore'          : ['@ignore'],
            '@implements'      : ['@implements',                             '{${1:InterfaceTypeName}}'],
            '@inheritdoc'      : ['@inheritdoc'],
            '@inner'           : ['@inner'],
            '@instance'        : ['@instance'],
            '@interface'       : ['@interface',                              '${1:OptionalName}'],
            '@kind'            : ['@kind',            '${1:class|constant|event|external|file|function|member|mixin|module|namespace|typedef}'],
            '@lends'           : ['@lends',                                  '${1:namepath}'],
            '@license'         : ['@license',                                '${1:identifier}'],
            '@listens'         : ['@listens',                                '${1:event}'],
            '@link'            : ['[${1:Optional link text}]{@link ${2:namepathOrURL}'],
            '@linkcode'        : ['[${1:Optional link text}]{@linkcode ${2:namepathOrURL}'],
            '@linkplain'       : ['[${1:Optional link text}]{@linkplain ${2:namepathOrURL}'],
            '@member'          : ['@member',          '{${1:Type}}',         '${2:name}'],
            '@memberof'        : ['@memberof',                               '${1:parentNamepath}'],
            '@memberof!'       : ['@memberof!',                              '${1:parentNamepath}'],
            '@method'          : ['@method',                                 '${1:optionalFunctionName}'],
            '@mixes'           : ['@mixes',                                  '${1:ObjectNamepath}'],
            '@mixin'           : ['@mixin',                                  '${1:OptionalMixinName}'],
            '@module'          : ['@module',          '{${1:OptionalType}}', '${2:OptionalName}'],
            '@name'            : ['@name',                                   '${1:namepath}'],
            '@namespace'       : ['@namespace',       '{${1:OptionalType}}', '${2:OptionalName}'],
            '@override'        : ['@override'],
            '@overview'        : ['@overview',                                                            '${1:Optional description.}'],
            '@package'         : ['@package'],
            '@param'           : ['@param',           '{${1:Type}}',         '${2:name}',                 '${3:Description.}'],
            '@private'         : ['@private'],
            '@prop'            : ['@prop',            '{${1:Type}}',         '${2:name}',                 '${3:Description.}'],
            '@property'        : ['@property',        '{${1:Type}}',         '${2:name}',                 '${3:Description.}'],
            '@protected'       : ['@protected'],
            '@public'          : ['@public'],
            '@readonly'        : ['@readonly'],
            '@requires'        : ['@requires',                               '${1:ModuleName}'],
            '@return'          : ['@return',          '{${1:Type}}',                                      '${2:Description.}'],
            '@returns'         : ['@returns',         '{${1:Type}}',                                      '${2:Description.}'],
            '@see'             : ['@see',                                    '${1:namepath|Text.}'],
            '@since'           : ['@since',                                  '${1:version}'],
            '@static'          : ['@static'],
            '@summary'         : ['@summary',                                                             '${1:Short summary.}'],
            '@this'            : ['@this',                                   '${1:namepath}'],
            '@throws'          : ['@throws',          '{${1:Type}}',                                      '${2:Description.}'],
            '@todo'            : ['@todo',                                                                '${1:Description.}'],
            '@tutorial'        : ['@tutorial',                               '${1:tutorial-identifier}'],
            '@type'            : ['@type',            '{${1:Type}}'],
            '@typedef'         : ['@typedef',         '{${1:OptionalType}}', '${2:namepath}'],
            '@variation'       : ['@variation',                              '${1:variation number}'],
            '@var'             : ['@var',             '{${1:Type}}',         '${2:name}'],
            '@version'         : ['@version',                                '${1:version}'],
            '@virtual'         : ['@virtual'],
            '@yield'           : ['@yield',           '{${1:Type}}',                                      '${2:Description.}'],
            '@yields'          : ['@yields',          '{${1:Type}}',                                      '${2:Description.}']
        }
        #self.completion_prefix_dict_for_tags = {}
        #
        #for key, value in self.completion_dict_for_tags.items():
        #    prefix = key[1]
        #    self.completion_prefix_dict_for_tags.setdefault(prefix, []).append((key, value))
        #
        self.default_completions_list_for_tags = []


    def on_query_completions(self, view, prefix, locations):
        #print('JSDocs query completions') # DEBUG
        # [Sanity Check] Only trigger within JSDoc documentation scopes.
        if not view.match_selector(locations[0], 'comment'):
            return []

        # Build the default completion list if it hasn’t been built already.
        if len(self.default_completions_list_for_tags) == 0:
            self.build_default_completions_list_for_tags(view)

        return self.get_completions(view, prefix, locations)


    def build_default_completions_list_for_tags(self, view):
        tag_spaces_count = view.settings().get('jsdocs_min_spaces_between_columns', 1)
        tag_spaces = ' ' * tag_spaces_count

        for key, value in self.completion_dict_for_tags.items():
            if len(value) == 1:
                self.default_completions_list_for_tags.append((key, value[0]))
            else:
                self.default_completions_list_for_tags.append((key, tag_spaces.join(value)))


    def get_completions(self, view, prefix, locations):
        current_index = locations[0]
        current_line = view.line(current_index)

        print('')

        previous_chars_index = current_index - len(prefix)
        previous_1_char  = view.substr(sublime.Region(previous_chars_index - 1, previous_chars_index))
        previous_2_chars = view.substr(sublime.Region(previous_chars_index - 2, previous_chars_index))
        previous_3_chars = view.substr(sublime.Region(previous_chars_index - 3, previous_chars_index))
        previous_4_chars = view.substr(sublime.Region(previous_chars_index - 4, previous_chars_index))


        print('')
        print('    prefix:           ', prefix)
        print('    location[0]:      ', current_index)
        print('    substr:           ', '"' + view.substr(sublime.Region(current_index, current_index + 3)) + '"')
        print('    previous_1_char:  ', '"' + previous_1_char + '"')
        print('    previous_4_chars: ', '"' + previous_4_chars + '"')
        print('')


        if '@' not in previous_4_chars:
            #print('NO `@` IN PREVIOUS 4 CHARS: "%s"' % previous_4_chars) # DEBUG
            return None

        # Look for a tag on the current line.
        tag_matches = get_tag_match(view, current_line)

        # If the current line doesn’t have a tag, look above and below.
        if not tag_matches:
            has_lines_above = not (region_is_first(view, current_line) or region_has_doc_start(view, current_line))
            has_lines_below = not (region_is_last (view, current_line) or region_has_doc_end  (view, current_line))

            # Search for a tag above the current line if there are doc-comment lines above it.
            if has_lines_above:
                tag_matches = self.get_tag_before(view, current_line)

            # If no tag was found and there are doc-comment lines below the current line then search
            # for a tag below.
            if not tag_matches and has_lines_below:
                tag_matches = self.get_tag_after(view, current_line)

        #if prefix == '':
        #    return (self.default_completions_list_for_tags, sublime.INHIBIT_WORD_COMPLETIONS)

        completion_list = []

        if tag_matches:
            print('TAG MATCHES:', tag_matches.groups())
            spaces_list = [
                tag_matches.group('type_spaces'),
                tag_matches.group('description_1_spaces'),
                tag_matches.group('description_2_spaces')
            ]
            completion_list = self.build_completion_list_for_tags(view, prefix, locations, spaces_list)
        else:
            completion_list = self.default_completions_list_for_tags

        # if previous_1_char == '@':
        #     completion_list = self.completion_prefix_dict_for_tags.get(prefix[0], [])

        # # match completion list using prefix
        # #completion_list = self.completion_prefix_dict.get(prefix[0], [])

        flags = sublime.INHIBIT_WORD_COMPLETIONS

        return (completion_list, flags)


    def get_tag_before(self, view, line):
        #print('GET TAG BEFORE %s' % line.begin()) # DEBUG
        while True:
            # Move to the previous line.
            line = get_prev_line(view, line)
            # Try and match a tag.
            tag_match = get_tag_match(view, line)

            #print('  LINE %s' % line.begin()) # DEBUG

            # Return the match if a tag matched.
            if tag_match:
                #print('  HAS TAG BEFORE') # DEBUG
                return tag_match

            # If the line is the first line or if it has the start of the doc comment then there’s
            # no match.
            if region_is_first(view, line) or region_has_doc_start(view, line):
                #print('  LINE IS FIRST') if region_is_first(view, line) else print('LINE HAS DOC START') # DEBUG
                return False

            # If the line ending is no longer part of a comment there’s no need to keep looking.
            if not view.match_selector(line.end(), 'comment'):
                #print('  LINE ENDING IS NO LONGER IN COMMENT') # DEBUG
                return False


    def get_tag_after(self, view, line):
        #print('GET TAG AFTER %s' % line.begin()) # DEBUG
        while True:
            # Move to the previous line.
            line = get_next_line(view, line)
            # Try and match a tag.
            tag_match = get_tag_match(view, line)

            #print('  LINE %s' % line.begin()) # DEBUG

            # Return the match if a tag matched.
            if tag_match:
                #print('  HAS TAG AFTER') # DEBUG
                return tag_match

            # If the line is the last line or if it has the end of the doc comment then there’s no
            # match.
            if region_is_last(view, line) or region_has_doc_end(view, line):
                #print('  LINE IS LAST') if region_is_last(view, line) else print('LINE HAS DOC END') # DEBUG
                return False

            # If the line beginning is no longer part of a comment there’s no need to keep looking.
            if not view.match_selector(line.begin(), 'comment'):
                #print('  LINE BEGINNING IS NO LONGER IN COMMENT') # DEBUG
                return False



    # """
    # Generate a completion list for JSDoc tags.
    # """
    def build_completion_list_for_tags(self, view, prefix, locations, spaces_list):
        spaces_default_count = view.settings().get('jsdocs_min_spaces_between_columns', 1)
        spaces_default = ' ' * spaces_default_count
        spaces_list_length = len(spaces_list)
        completions_list = []

        for key, tag_parts in self.completion_dict_for_tags.items():
            completion = ''

            if spaces_list_length != 0:
                for i, tag_part in enumerate(tag_parts):
                    spaces = spaces_list[i] if i < spaces_list_length and spaces_list[i] and len(spaces_list[i]) >= spaces_default_count else spaces_default
                    completion += tag_part + (spaces or spaces_default)

                completion = completion.strip()
            else:
                completion = spaces_default.join(tag_parts)

            completions_list.append((key + '\tJSDoc', completion))

        return completions_list

        #self.completion_list_for_tags = tag_completions_list

        # construct a dictionary where the key is the first character of the completion and the
        # value is the completion.
        #for completion in tag_completions_list:
        #    first_letter = completion[0][1]
        #    self.completion_prefix_dict_for_tags.setdefault(first_letter, []).append(completion)

    # def on_selection_modified(self, view):
    #     if len(view.sel()) != 1:
    #         return
    #     first_selection = view.sel()[0]
    #     if first_selection.size() == 0:
    #         return
    #     if not view.match_selector(first_selection.begin(), 'comment.block'):
    #         return
    #     print(view.substr(first_selection))
