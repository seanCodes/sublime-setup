"""
DocBlockr v2.14.1
by Nick Fisher, and all the great people listed in CONTRIBUTORS.md
https://github.com/spadgos/sublime-jsdocs

*** Please read CONTIBUTING.md before sending pull requests. Thanks! ***

"""
import sublime
import sublime_plugin
import re
import datetime
import time
import imp
from functools import reduce

def read_line(view, point):
    if (point >= view.size()):
        return

    next_line = view.line(point)
    return view.substr(next_line)


def write(view, str):
    view.run_command(
        'insert_snippet', {
            'contents': str
        }
    )


def counter():
    count = 0
    while True:
        count += 1
        yield(count)


def escape(str):
    return str.replace('$', '\$').replace('{', '\{').replace('}', '\}')


def is_numeric(val):
    try:
        float(val)
        return True
    except ValueError:
        return False


def getParser(view):
    scope = view.scope_name(view.sel()[0].end())
    res = re.search('\\bsource\\.([a-z+\-]+)', scope)
    sourceLang = res.group(1) if res else 'js'
    viewSettings = view.settings()

    if sourceLang == "php":
        return JsdocsPHP(viewSettings)
    elif sourceLang == "coffee":
        return JsdocsCoffee(viewSettings)
    elif sourceLang == "actionscript" or sourceLang == 'haxe':
        return JsdocsActionscript(viewSettings)
    elif sourceLang == "c++" or sourceLang == 'c' or sourceLang == 'cuda-c++':
        return JsdocsCPP(viewSettings)
    elif sourceLang == 'objc' or sourceLang == 'objc++':
        return JsdocsObjC(viewSettings)
    elif sourceLang == 'java' or sourceLang == 'groovy' or sourceLang == 'apex':
        return JsdocsJava(viewSettings)
    elif sourceLang == 'rust':
        return JsdocsRust(viewSettings)
    elif sourceLang == 'ts':
        return JsdocsTypescript(viewSettings)
    return JsdocsJavascript(viewSettings)


def splitByCommas(str):
    """
    Split a string by unenclosed commas: that is, commas which are not inside of quotes or brackets.
    splitByCommas('foo, bar(baz, quux), fwip = "hey, hi"')
     ==> ['foo', 'bar(baz, quux)', 'fwip = "hey, hi"']
    """
    out = []

    if not str:
        return out

    # the current token
    current = ''

    # characters which open a section inside which commas are not separators between different arguments
    openQuotes = '"\'<({'
    # characters which close the section. The position of the character here should match the opening
    # indicator in `openQuotes`
    closeQuotes = '"\'>)}'

    matchingQuote = ''
    insideQuotes = False
    nextIsLiteral = False

    for char in str:
        if nextIsLiteral:  # previous char was a \
            current += char
            nextIsLiteral = False
        elif insideQuotes:
            if char == '\\':
                nextIsLiteral = True
            else:
                current += char
                if char == matchingQuote:
                    insideQuotes = False
        else:
            if char == ',':
                out.append(current.strip())
                current = ''
            else:
                current += char
                quoteIndex = openQuotes.find(char)
                if quoteIndex > -1:
                    matchingQuote = closeQuotes[quoteIndex]
                    insideQuotes = True

    out.append(current.strip())
    return out


def flatten(theList):
    """
    Flatten a shallow list. Only works when all items are lists.
    [[(1,1)], [(2,2), (3, 3)]] --> [(1,1), (2,2), (3,3)]
    """
    return [item for sublist in theList for item in sublist]

def getDocBlockRegion(view, point):
    """
    Given a starting point inside a DocBlock, return a Region which encompasses the entire block.
    This is similar to `run_command('expand_selection', { to: 'scope' })`, however it is resilient to bugs which occur
    due to language files adding scopes inside the DocBlock (eg: to highlight tags)
    """
    start = end = point
    while start > 0 and view.scope_name(start - 1).find('comment.block') > -1:
        start = start - 1

    while end < view.size() and view.scope_name(end).find('comment.block') > -1:
        end = end + 1

    return sublime.Region(start, end)

def parseJSDocTag(text):
    text = text.strip()
    tag  = getMatch(r'^@\w+', text)
    if not tag:
        #print('    - TEXT HAS NO TAG -') # DEBUG
        return None
    tagPatternDict = {
        '@abstract'        : '*',
        '@access'          : '*',
        '@alias'           : '*',
        '@arg'             : 'type name *',
        '@argument'        : 'type name *',
        '@async'           : '*',
        '@augments'        : '*',
        '@author'          : 'personname email?',
        '@borrows'         : 'name as name',
        '@callback'        : '*',
        '@class'           : '*',
        '@classdesc'       : '*',
        '@const'           : 'type? *',
        '@constant'        : 'type? *',
        '@constructor'     : '*',
        '@constructs'      : '*',
        '@copyright'       : '*',
        '@default'         : '*',
        '@defaultvalue'    : '*',
        '@deprecated'      : '*',
        '@desc'            : '*',
        '@description'     : '*',
        '@emits'           : '*',
        '@enum'            : '*',
        '@event'           : '*',
        '@example'         : 'caption? example?', # example could come after tag
        '@exception'       : 'type *',
        '@exports'         : '*',
        '@extends'         : '*',
        '@external'        : '*',
        '@file'            : '*',
        '@fileoverview'    : '*',
        '@fires'           : '*',
        '@func'            : '*',
        '@function'        : '*',
        '@global'          : '*',
        '@generator'       : '*',
        '@hideconstructor' : '*',
        '@host'            : '*',
        '@ignore'          : '*',
        '@implements'      : '*',
        '@inheritdoc'      : '*',
        '@inner'           : '*',
        '@instance'        : '*',
        '@interface'       : '*',
        '@kind'            : '*',
        '@lends'           : '*',
        '@license'         : '*',
        '@listens'         : '*',
        '@link'            : 'link',
        '@linkcode'        : 'link',
        '@linkplain'       : 'link',
        '@member'          : 'type *',
        '@memberof'        : '*',
        '@method'          : '*',
        '@mixes'           : '*',
        '@mixin'           : '*',
        '@module'          : '*',
        '@name'            : '*',
        '@namespace'       : 'type *',
        '@override'        : '*',
        '@overview'        : '*',
        '@package'         : '*',
        '@param'           : 'type name *',
        '@private'         : '*',
        '@prop'            : 'type name *',
        '@property'        : 'type name *',
        '@protected'       : '*',
        '@public'          : '*',
        '@readonly'        : '*',
        '@requires'        : '*',
        '@return'          : 'type *',
        '@returns'         : 'type *',
        '@see'             : '*',
        '@since'           : '*',
        '@static'          : '*',
        '@summary'         : '*',
        '@this'            : '*',
        '@throws'          : 'type *',
        '@todo'            : '*',
        '@tutorial'        : '*',
        '@type'            : '*',
        '@typedef'         : 'type? *',
        '@variation'       : '*',
        '@var'             : 'type *',
        '@version'         : '*',
        '@virtual'         : '*',
        '@yield'           : 'type *',
        '@yields'          : 'type *'
    }
    tagPatternRegexDict = {
        '*'                 : r'(?P<tag>@\w+)[ \t]*(?P<rest>\S.*)?',
        'type *'            : r'(?P<tag>@\w+)[ \t]+(?P<type>\{.*?\})[ \t]*(?P<rest>\S.*)?',
        'type? *'           : r'(?P<tag>@\w+)[ \t]*(?P<type>\{.*?\})?[ \t]+(?P<rest>\S.*)',
        'type name *'       : r'(?P<tag>@\w+)[ \t]+(?P<type>\{.*?\})[ \t]*(?P<name>\[.*?\]|\S+)?[ \t]*(?P<rest>\S.*)?',
        'personname email?' : r'(?P<tag>@\w+)[ \t]+(?P<name>\S+(?: +[^<\s]+)*)[ \t]*(?P<email><.*?>)?',
        'name as name'      : r'(?P<tag>@\w+)[ \t]+(?P<name1>\S+)[ \t]+(?P<as>as)[ \t]+(?P<name2>\S+)',
        'caption? example?' : r'(?P<tag>@\w+)[ \t]*(?P<caption><caption>.*?</caption>)?(?P<rest>\S.*)?',
        'link'              : r''
    }
    pattern = tagPatternDict[tag] if tag in tagPatternDict else '*'
    regex = tagPatternRegexDict[tagPatternDict[tag]] if tag in tagPatternDict else tagPatternRegexDict['*']
    #match = re.match(regex, text)
    #if match is None: return ''
    #groups = match.groups('')
    #length = len(groups)
    #if length and 'rest' in match.groupdict():
    #    print(match.groupdict('no')['rest'])
    #else:
    #    print('no')
    #return groups if length else match.group(0)
    return getMatch(regex, text)


def getMatch(regex, text, groupIndex=None):
    match = re.match(regex, text)
    if match is None: return ''
    groups = match.groups('')
    length = len(groups)
    if groupIndex is not None and groupIndex <= length:
        return match.group(groupIndex)
    return groups if length else match.group(0)


class JsdocsCommand(sublime_plugin.TextCommand):

    def run(self, edit, inline=False):

        self.initialize(self.view, inline)

        if self.parser.isExistingComment(self.line):
            write(self.view, "\n *" + self.indentSpaces)
            return

        # erase characters in the view (will be added to the output later)
        self.view.erase(edit, self.trailingRgn)

        # match against a function declaration.
        out = self.parser.parse(self.line)

        snippet = self.generateSnippet(out, inline)

        write(self.view, snippet)

    def initialize(self, view, inline=False):
        point = view.sel()[0].end()

        self.settings = view.settings()

        # trailing characters are put inside the body of the comment
        self.trailingRgn = sublime.Region(point, view.line(point).end())
        self.trailingString = view.substr(self.trailingRgn).strip()
        # drop trailing '*/'
        self.trailingString = escape(re.sub('\\s*\\*\\/\\s*$', '', self.trailingString))

        self.indentSpaces = " " * max(0, self.settings.get("jsdocs_indentation_spaces", 1))
        self.prefix = "*"

        settingsAlignTags = self.settings.get("jsdocs_align_tags", 'deep')
        self.deepAlignTags = settingsAlignTags == 'deep'
        self.shallowAlignTags = settingsAlignTags in ('shallow', True)

        self.parser = parser = getParser(view)
        parser.inline = inline

        # use trailing string as a description of the function
        if self.trailingString:
            parser.setNameOverride(self.trailingString)

        # read the next line
        self.line = parser.getDefinition(view, view.line(point).end() + 1)

    def generateSnippet(self, out, inline=False):
        # substitute any variables in the tags

        if out:
            out = self.substituteVariables(out)

        # align the tags
        if out and (self.shallowAlignTags or self.deepAlignTags) and not inline:
            out = self.alignTags(out)

        # fix all the tab stops so they're consecutive
        if out:
            out = self.fixTabStops(out)

        if inline:
            if out:
                return " " + out[0] + " */"
            else:
                return " $0 */"
        else:
            return self.createSnippet(out) + ('\n' if self.settings.get('jsdocs_newline_after_block') else '')

    def alignTags(self, out):
        def outputWidth(str):
            # get the length of a string, after it is output as a snippet,
            # "${1:foo}" --> 3
            return len(re.sub("[$][{]\\d+:([^}]+)[}]", "\\1", str).replace('\$', '$'))

        # count how many columns we have
        maxCols = 0
        # this is a 2d list of the widths per column per line
        widths = []

        # Grab the return tag if required.
        if self.settings.get('jsdocs_per_section_indent'):
            returnTag = self.settings.get('jsdocs_return_tag') or '@return'
        else:
            returnTag = False

        for line in out:
            if line.startswith('@'):
                # Ignore the return tag if we're doing per-section indenting.
                if returnTag and line.startswith(returnTag):
                    continue
                # ignore all the words after `@author`
                columns = line.split(" ") if not line.startswith('@author') else ['@author']
                widths.append(list(map(outputWidth, columns)))
                maxCols = max(maxCols, len(widths[-1]))

        #  initialise a list to 0
        maxWidths = [0] * maxCols

        if (self.shallowAlignTags):
            maxCols = 1

        for i in range(0, maxCols):
            for width in widths:
                if (i < len(width)):
                    maxWidths[i] = max(maxWidths[i], width[i])

        # Convert to a dict so we can use .get()
        maxWidths = dict(enumerate(maxWidths))

        # Minimum spaces between line columns
        minColSpaces = self.settings.get('jsdocs_min_spaces_between_columns', 1)

        for index, line in enumerate(out):
            # format the spacing of columns, but ignore the author tag. (See #197)
            if line.startswith('@') and not line.startswith('@author'):
                newOut = []
                for partIndex, part in enumerate(line.split(" ")):
                    newOut.append(part)
                    newOut.append(" " * minColSpaces + (" " * (maxWidths.get(partIndex, 0) - outputWidth(part))))
                out[index] = "".join(newOut).strip()

        return out

    def substituteVariables(self, out):
        def getVar(match):
            varName = match.group(1)
            if varName == 'datetime':
                date = datetime.datetime.now().replace(microsecond=0)
                offset = time.timezone / -3600.0
                return "%s%s%02d%02d" % (
                    date.isoformat(),
                    '+' if offset >= 0 else "-",
                    abs(offset),
                    (offset % 1) * 60
                )
            elif varName == 'date':
                return datetime.date.today().isoformat()
            else:
                return match.group(0)

        def subLine(line):
            return re.sub(r'\{\{([^}]+)\}\}', getVar, line)

        return list(map(subLine, out))

    def fixTabStops(self, out):
        tabIndex = counter()

        def swapTabs(m):
            return "%s%d%s" % (m.group(1), next(tabIndex), m.group(2))

        for index, outputLine in enumerate(out):
            out[index] = re.sub("(\\$\\{)\\d+(:[^}]+\\})", swapTabs, outputLine)

        return out

    def createSnippet(self, out):
        snippet = ""
        closer = self.parser.settings['commentCloser']
        if out:
            if self.settings.get('jsdocs_spacer_between_sections') == True:
                lastTag = None
                for idx, line in enumerate(out):
                    res = re.match("^\\s*@([a-zA-Z]+)", line)
                    if res and (lastTag != res.group(1)):
                        if self.settings.get('jsdocs_function_description') == False:
                            if lastTag != None:
                                out.insert(idx, "")
                        else:
                            out.insert(idx, "")
                        lastTag = res.group(1)
            elif self.settings.get('jsdocs_spacer_between_sections') == 'after_description' and self.settings.get('jsdocs_function_description'):
                lastLineIsTag = False
                for idx, line in enumerate(out):
                    res = re.match("^\\s*@([a-zA-Z]+)", line)
                    if res:
                        if not lastLineIsTag:
                            out.insert(idx, "")
                        lastLineIsTag = True
            for line in out:
                snippet += "\n " + self.prefix + (self.indentSpaces + line if line else "")
        else:
            snippet += "\n " + self.prefix + self.indentSpaces + "${0:" + self.trailingString + '}'

        snippet += "\n" + closer
        return snippet


class JsdocsParser(object):

    def __init__(self, viewSettings):
        self.viewSettings = viewSettings
        self.setupSettings()
        self.nameOverride = None

    def isExistingComment(self, line):
        return re.search('^\\s*\\*', line)

    def setNameOverride(self, name):
        """ overrides the description of the function - used instead of parsed description """
        self.nameOverride = name

    def getNameOverride(self):
        return self.nameOverride

    def parse(self, line):
        if self.viewSettings.get('jsdocs_simple_mode'):
            return None

        try:
            out = self.parseFunction(line)  # (name, args, retval, options)
            if (out):
                return self.formatFunction(*out)

            out = self.parseVar(line)
            if out:
                return self.formatVar(*out)
        except:
            # TODO show exception if dev\debug mode
            return None

        return None

    def formatVar(self, name, val, valType=None):
        out = []
        if not valType:
            if not val or val == '':  # quick short circuit
                valType = "[type]"
            else:
                valType = self.guessTypeFromValue(val) or self.guessTypeFromName(name) or "[type]"
        if self.inline:
            out.append("@%s %s${1:%s}%s ${1:[description]}" % (
                self.settings['typeTag'],
                "{" if self.settings['curlyTypes'] else "",
                valType,
                "}" if self.settings['curlyTypes'] else ""
            ))
        else:
            out.append("${1:[%s description]}" % (escape(name)))
            out.append("@%s %s${1:%s}%s" % (
                self.settings['typeTag'],
                "{" if self.settings['curlyTypes'] else "",
                valType,
                "}" if self.settings['curlyTypes'] else ""
            ))

        return out

    def getTypeInfo(self, argType, argName):
        typeInfo = ''
        if self.settings['typeInfo']:
            typeInfo = '%s${1:%s}%s ' % (
                "{" if self.settings['curlyTypes'] else "",
                escape(argType or self.guessTypeFromName(argName) or "[type]"),
                "}" if self.settings['curlyTypes'] else "",
            )

        return typeInfo

    def formatFunction(self, name, args, retval, options={}):
        out = []
        if 'as_setter' in options:
            out.append('@private')
            return out

        extraTagAfter = self.viewSettings.get("jsdocs_extra_tags_go_after") or False

        description = self.getNameOverride() or ('[%s%sdescription]' % (escape(name), ' ' if name else ''))
        if self.viewSettings.get('jsdocs_function_description'):
            out.append("${1:%s}" % description)

        if (self.viewSettings.get("jsdocs_autoadd_method_tag") is True):
            out.append("@%s %s" % (
                "method",
                escape(name)
            ))

        if not extraTagAfter:
            self.addExtraTags(out)

        # if there are arguments, add a @param for each
        if (args):
            # remove comments inside the argument list.
            args = re.sub(r'/\*.*?\*/', '', args)
            for argType, argName in self.parseArgs(args):
                typeInfo = self.getTypeInfo(argType, argName)

                format_str = "@param %s%s"
                if (self.viewSettings.get('jsdocs_param_description')):
                    format_str += " ${1:[description]}"

                out.append(format_str % (
                    typeInfo,
                    escape(argName) if self.viewSettings.get('jsdocs_param_name') else ''
                ))

        # return value type might be already available in some languages but
        # even then ask language specific parser if it wants it listed
        retType = self.getFunctionReturnType(name, retval)
        if retType is not None:
            typeInfo = ''
            if self.settings['typeInfo']:
                typeInfo = ' %s${1:%s}%s' % (
                    "{" if self.settings['curlyTypes'] else "",
                    retType or "[type]",
                    "}" if self.settings['curlyTypes'] else ""
                )
            format_args = [
                self.viewSettings.get('jsdocs_return_tag') or '@return',
                typeInfo
            ]

            if (self.viewSettings.get('jsdocs_return_description')):
                format_str = "%s%s %s${1:[description]}"
                third_arg = ""

                # the extra space here is so that the description will align with the param description
                if args and self.viewSettings.get('jsdocs_align_tags') == 'deep':
                    if not self.viewSettings.get('jsdocs_per_section_indent'):
                        third_arg = " "

                format_args.append(third_arg)
            else:
                format_str = "%s%s"

            out.append(format_str % tuple(format_args))

        for notation in self.getMatchingNotations(name):
            if 'tags' in notation:
                out.extend(notation['tags'])

        if extraTagAfter:
            self.addExtraTags(out)

        return out

    def getFunctionReturnType(self, name, retval):
        """ returns None for no return type. False meaning unknown, or a string """

        if re.match("[A-Z]", name):
            # no return, but should add a class
            return None

        if re.match('[$_]?(?:set|add)($|[A-Z_])', name):
            # setter/mutator, no return
            return None

        if re.match('[$_]?(?:is|has)($|[A-Z_])', name):  # functions starting with 'is' or 'has'
            return self.settings['bool']

        return self.guessTypeFromName(name) or False

    def parseArgs(self, args):
        """
        a list of tuples, the first being the best guess at the type, the second being the name
        """
        blocks = splitByCommas(args)
        out = []
        for arg in blocks:
            out.append(self.getArgInfo(arg))

        return flatten(out)

    def getArgInfo(self, arg):
        """
        Return a list of tuples, one for each argument derived from the arg param.
        """
        return [(self.getArgType(arg), self.getArgName(arg))]

    def getArgType(self, arg):
        return None

    def getArgName(self, arg):
        return arg

    def addExtraTags(self, out):
        extraTags = self.viewSettings.get('jsdocs_extra_tags', [])
        if (len(extraTags) > 0):
            out.extend(extraTags)

    def guessTypeFromName(self, name):
        matches = self.getMatchingNotations(name)
        if len(matches):
            rule = matches[0]
            if ('type' in rule):
                return self.settings[rule['type']] if rule['type'] in self.settings else rule['type']

        if (re.match("(?:is|has)[A-Z_]", name)):
            return self.settings['bool']

        if (re.match("^(?:cb|callback|done|next|fn)$", name)):
            return self.settings['function']

        return False

    def getMatchingNotations(self, name):
        def checkMatch(rule):
            if 'prefix' in rule:
                regex = re.escape(rule['prefix'])
                if re.match('.*[a-z]', rule['prefix']):
                    regex += '(?:[A-Z_]|$)'
                return re.match(regex, name)
            elif 'regex' in rule:
                return re.search(rule['regex'], name)

        return list(filter(checkMatch, self.viewSettings.get('jsdocs_notation_map', [])))

    def getDefinition(self, view, pos):
        """
        get a relevant definition starting at the given point
        returns string
        """
        maxLines = 25  # don't go further than this
        openBrackets = 0

        definition = ''

        # count the number of open parentheses
        def countBrackets(total, bracket):
            return total + (1 if bracket == '(' else -1)

        for i in range(0, maxLines):
            line = read_line(view, pos)
            if line is None:
                break

            pos += len(line) + 1
            # strip comments
            line = re.sub(r"//.*",     "", line)
            line = re.sub(r"/\*.*\*/", "", line)

            searchForBrackets = line

            # on the first line, only start looking from *after* the actual function starts. This is
            # needed for cases like this:
            # (function (foo, bar) { ... })
            if definition == '':
                opener = re.search(self.settings['fnOpener'], line) if self.settings['fnOpener'] else False
                if opener:
                    # ignore everything before the function opener
                    searchForBrackets = line[opener.start():]

            openBrackets = reduce(countBrackets, re.findall('[()]', searchForBrackets), openBrackets)

            definition += line
            if openBrackets == 0:
                break
        return definition


class JsdocsJavascript(JsdocsParser):
    def setupSettings(self):
        identifier = '[a-zA-Z_$][a-zA-Z_$0-9]*'
        self.settings = {
            # curly brackets around the type information
            "curlyTypes": True,
            'typeInfo': True,
            "typeTag": self.viewSettings.get('jsdocs_override_js_var') or "type",
            # technically, they can contain all sorts of unicode, but w/e
            "varIdentifier": identifier,
            "fnIdentifier":  identifier,
            "fnOpener": '(?:'
                    + r'function[\s*]*(?:' + identifier + r')?\s*\('
                    + '|'
                    + '(?:' + identifier + r'|\(.*\)\s*=>)'
                    + '|'
                    + '(?:' + identifier + r'\s*\(.*\)\s*\{)'
                    + ')',
            "commentCloser": " */",
            "bool": "Boolean",
            "function": "Function"
        }

    def parseFunction(self, line):
        res = re.search(
            # Normal functions...
            #   fnName = function,  fnName : function
            r'(?:(?P<name1>' + self.settings['varIdentifier'] + r')\s*[:=]\s*)?'
            + 'function'
            # function fnName, function* fnName
            + r'(?P<generator>[\s*]+)?(?P<name2>' + self.settings['fnIdentifier'] + ')?'
            # (arg1, arg2)
            + r'\s*\(\s*(?P<args>.*)\)',
            line
        ) or re.search(
            # ES6 arrow functions
            # () => y,  x => y,  (x, y) => y,  (x = 4) => y
            r'(?:(?P<args>' + self.settings['varIdentifier'] + r')|\(\s*(?P<args2>.*)\))\s*=>',
            line
        ) or re.search(
            # ES6 method initializer shorthand
            # var person = { getName() { return this.name; } }
            r'(?P<name1>' + self.settings['varIdentifier'] + ')\s*\((?P<args>.*)\)\s*\{',
            line
        )
        if not res:
            return None

        groups = {
            'name1': '',
            'name2': '',
            'generator': '',
            'args': '',
            'args2': ''
        }
        groups.update(res.groupdict())
        # grab the name out of "name1 = function name2(foo)" preferring name1
        generatorSymbol = '*' if (groups['generator'] or '').find('*') > -1 else ''
        name = generatorSymbol + (groups['name1'] or groups['name2'] or '')
        args = groups['args'] or groups['args2'] or ''

        return (name, args, None)

    def parseVar(self, line):
        res = re.search(
            #   var foo = blah,
            #       foo = blah;
            #   baz.foo = blah;
            #   baz = {
            #        foo : blah
            #   }

            '(?P<name>' + self.settings['varIdentifier'] + ')\s*[=:]\s*(?P<val>.*?)(?:[;,]|$)',
            line
        )
        if not res:
            return None

        return (res.group('name'), res.group('val').strip())

    def getArgInfo(self, arg):
        if (re.search('^\{.*\}$', arg)):
            subItems = splitByCommas(arg[1:-1])
            prefix = 'options.'
        else:
            subItems = [arg]
            prefix = ''

        out = []
        for subItem in subItems:
            out.append((self.getArgType(subItem), prefix + self.getArgName(subItem)))

        return out

    def getArgType(self, arg):
        parts = re.split(r'\s*=\s*', arg, 1)
        # rest parameters
        if parts[0].find('...') == 0:
            return '...[type]'
        elif len(parts) > 1:
            return self.guessTypeFromValue(parts[1])

    def getArgName(self, arg):
        namePart = re.split(r'\s*=\s*', arg, 1)[0]

        # check for rest parameters, eg: function (foo, ...rest) {}
        if namePart.find('...') == 0:
            return namePart[3:]
        return namePart

    def getFunctionReturnType(self, name, retval):
        if name and name[0] == '*':
            return None
        return super(JsdocsJavascript, self).getFunctionReturnType(name, retval)

    def getMatchingNotations(self, name):
        out = super(JsdocsJavascript, self).getMatchingNotations(name)
        if name and name[0] == '*':
            # if '@returns' is preferred, then also use '@yields'. Otherwise, '@return' and '@yield'
            yieldTag = '@yield' + ('s' if self.viewSettings.get('jsdocs_return_tag', '_')[-1] == 's' else '')
            description = ' ${1:[description]}' if self.viewSettings.get('jsdocs_return_description', True) else ''
            out.append({ 'tags': [
                '%s {${1:[type]}}%s' % (yieldTag, description)
            ]})
        return out

    def guessTypeFromValue(self, val):
        lowerPrimitives = self.viewSettings.get('jsdocs_lower_case_primitives') or False
        shortPrimitives = self.viewSettings.get('jsdocs_short_primitives') or False
        if is_numeric(val):
            return "number" if lowerPrimitives else "Number"
        if val[0] == '"' or val[0] == "'":
            return "string" if lowerPrimitives else "String"
        if val[0] == '[':
            return "Array"
        if val[0] == '{':
            return "Object"
        if val == 'true' or val == 'false':
            returnVal = 'Bool' if shortPrimitives else 'Boolean'
            return returnVal.lower() if lowerPrimitives else returnVal
        if re.match('RegExp\\b|\\/[^\\/]', val):
            return 'RegExp'
        if val.find('=>') > -1:
            return 'function' if lowerPrimitives else 'Function'
        if val[:4] == 'new ':
            res = re.search('new (' + self.settings['fnIdentifier'] + ')', val)
            return res and res.group(1) or None
        return None


class JsdocsPHP(JsdocsParser):
    def setupSettings(self):
        shortPrimitives = self.viewSettings.get('jsdocs_short_primitives') or False
        nameToken = '[a-zA-Z_\\x7f-\\xff][a-zA-Z0-9_\\x7f-\\xff]*'
        self.settings = {
            # curly brackets around the type information
            'curlyTypes': False,
            'typeInfo': True,
            'typeTag': "var",
            'varIdentifier': '&?[$]' + nameToken + '(?:->' + nameToken + ')*',
            'fnIdentifier': nameToken,
            'typeIdentifier': '\\\\?' + nameToken + '(\\\\' + nameToken + ')*',
            'fnOpener': 'function(?:\\s+' + nameToken + ')?\\s*\\(',
            'commentCloser': ' */',
            'bool': 'bool' if shortPrimitives else 'boolean',
            'function': "function"
        }

    def parseFunction(self, line):
        res = re.search(
            'function\\s+&?\\s*'
            + '(?P<name>' + self.settings['fnIdentifier'] + ')'
            # function fnName
            # (arg1, arg2)
            + '\\s*\\(\\s*(?P<args>.*)\\)',
            line
        )
        if not res:
            return None

        return (res.group('name'), res.group('args'), None)

    def getArgType(self, arg):

        res = re.search(
            '(?P<type>' + self.settings['typeIdentifier'] + ')?'
            + '\\s*(?P<name>' + self.settings['varIdentifier'] + ')'
            + '(\\s*=\\s*(?P<val>.*))?',
            arg
        );

        if (res):

            argType = res.group("type")
            argName = res.group("name")
            argVal = res.group("val")

            # function fnc_name(type $name = val)
            if (argType and argVal):

                # function fnc_name(array $x = array())
                # function fnc_name(array $x = [])
                argValType = self.guessTypeFromValue(argVal)
                if argType == argValType:
                    return argType

                # function fnc_name(type $name = null)
                return argType + "|" + argValType

            # function fnc_name(type $name)
            if (argType):
                return argType

            # function fnc_name($name = value)
            if (argVal):
                guessedType = self.guessTypeFromValue(argVal)
                return guessedType if guessedType != 'null' else None
        # function fnc_name()
        return None

    def getArgName(self, arg):
        return re.search("(" + self.settings['varIdentifier'] + ")(?:\\s*=.*)?$", arg).group(1)

    def parseVar(self, line):
        res = re.search(
            #   var $foo = blah,
            #       $foo = blah;
            #   $baz->foo = blah;
            #   $baz = array(
            #        'foo' => blah
            #   )

            '(?P<name>' + self.settings['varIdentifier'] + ')\\s*=>?\\s*(?P<val>.*?)(?:[;,]|$)',
            line
        )
        if res:
            return (res.group('name'), res.group('val').strip())

        res = re.search(
            '\\b(?:var|public|private|protected|static)\\s+(?P<name>' + self.settings['varIdentifier'] + ')',
            line
        )
        if res:
            return (res.group('name'), None)

        return None

    def guessTypeFromValue(self, val):
        shortPrimitives = self.viewSettings.get('jsdocs_short_primitives') or False
        if is_numeric(val):
            return "float" if '.' in val else 'int' if shortPrimitives else 'integer'
        if val[0] == '"' or val[0] == "'":
            return "string"
        if val[:5] == 'array' or (val[0] == '[' and val[-1] == ']'):
            return "array"
        if val.lower() in ('true', 'false', 'filenotfound'):
            return 'bool' if shortPrimitives else 'boolean'
        if val[:4] == 'new ':
            res = re.search('new (' + self.settings['fnIdentifier'] + ')', val)
            return res and res.group(1) or None
        if val.lower() in ('null'):
            return 'null'
        return None

    def getFunctionReturnType(self, name, retval):
        shortPrimitives = self.viewSettings.get('jsdocs_short_primitives') or False
        if (name[:2] == '__'):
            if name in ('__construct', '__destruct', '__set', '__unset', '__wakeup'):
                return None
            if name == '__sleep':
                return 'array'
            if name == '__toString':
                return 'string'
            if name == '__isset':
                return 'bool' if shortPrimitives else 'boolean'
        return JsdocsParser.getFunctionReturnType(self, name, retval)


class JsdocsCPP(JsdocsParser):
    def setupSettings(self):
        nameToken = '[a-zA-Z_][a-zA-Z0-9_]*'
        identifier = '(%s)(::%s)?' % (nameToken, nameToken)
        self.settings = {
            'typeInfo': False,
            'curlyTypes': False,
            'typeTag': 'param',
            'commentCloser': ' */',
            'fnIdentifier': identifier,
            'varIdentifier': '(' + identifier + ')\\s*(?:\\[(?:' + identifier + r')?\]|\((?:(?:\s*,\s*)?[a-z]+)+\s*\))*',
            'fnOpener': identifier + '\\s+' + identifier + '\\s*\\(',
            'bool': 'bool',
            'function': 'function'
        }

    def parseFunction(self, line):
        res = re.search(
            '(?P<retval>' + self.settings['varIdentifier'] + ')[&*\\s]+'
            + '(?P<name>' + self.settings['varIdentifier'] + ');?'
            # void fnName
            # (arg1, arg2)
            + '\\s*\\(\\s*(?P<args>.*)\)',
            line
        )
        if not res:
            return None

        return (res.group('name'), res.group('args'), res.group('retval'))

    def parseArgs(self, args):
        if args.strip() == 'void':
            return []
        return super(JsdocsCPP, self).parseArgs(args)

    def getArgType(self, arg):
        return None

    def getArgName(self, arg):
        return re.search(self.settings['varIdentifier'] + r"(?:\s*=.*)?$", arg).group(1)

    def parseVar(self, line):
        return None

    def guessTypeFromValue(self, val):
        return None

    def getFunctionReturnType(self, name, retval):
        return retval if retval != 'void' else None


class JsdocsCoffee(JsdocsParser):
    def setupSettings(self):
        identifier = '[a-zA-Z_$][a-zA-Z_$0-9]*'
        self.settings = {
            # curly brackets around the type information
            'curlyTypes': True,
            'typeTag': self.viewSettings.get('jsdocs_override_js_var') or "type",
            'typeInfo': True,
            # technically, they can contain all sorts of unicode, but w/e
            'varIdentifier': identifier,
            'fnIdentifier': identifier,
            'fnOpener': None,  # no multi-line function definitions for you, hipsters!
            'commentCloser': '###',
            'bool': 'Boolean',
            'function': 'Function'
        }

    def parseFunction(self, line):
        res = re.search(
            #   fnName = function,  fnName : function
            '(?:(?P<name>' + self.settings['varIdentifier'] + ')\s*[:=]\s*)?'
            + '(?:\\((?P<args>[^()]*?)\\))?\\s*([=-]>)',
            line
        )
        if not res:
            return None

        # grab the name out of "name1 = function name2(foo)" preferring name1
        name = res.group('name') or ''
        args = res.group('args')

        return (name, args, None)

    def parseVar(self, line):
        res = re.search(
            #   var foo = blah,
            #       foo = blah;
            #   baz.foo = blah;
            #   baz = {
            #        foo : blah
            #   }

            '(?P<name>' + self.settings['varIdentifier'] + ')\s*[=:]\s*(?P<val>.*?)(?:[;,]|$)',
            line
        )
        if not res:
            return None

        return (res.group('name'), res.group('val').strip())

    def guessTypeFromValue(self, val):
        lowerPrimitives = self.viewSettings.get('jsdocs_lower_case_primitives') or False
        if is_numeric(val):
            return "number" if lowerPrimitives else "Number"
        if val[0] == '"' or val[0] == "'":
            return "string" if lowerPrimitives else "String"
        if val[0] == '[':
            return "Array"
        if val[0] == '{':
            return "Object"
        if val == 'true' or val == 'false':
            return "boolean" if lowerPrimitives else "Boolean"
        if re.match('RegExp\\b|\\/[^\\/]', val):
            return 'RegExp'
        if val[:4] == 'new ':
            res = re.search('new (' + self.settings['fnIdentifier'] + ')', val)
            return res and res.group(1) or None
        return None


class JsdocsActionscript(JsdocsParser):

    def setupSettings(self):
        nameToken = '[a-zA-Z_][a-zA-Z0-9_]*'
        self.settings = {
            'typeInfo': False,
            'curlyTypes': False,
            'typeTag': '',
            'commentCloser': ' */',
            'fnIdentifier': nameToken,
            'varIdentifier': '(%s)(?::%s)?' % (nameToken, nameToken),
            'fnOpener': 'function(?:\\s+[gs]et)?(?:\\s+' + nameToken + ')?\\s*\\(',
            'bool': 'bool',
            'function': 'function'
        }

    def parseFunction(self, line):
        res = re.search(
            #   fnName = function,  fnName : function
            '(?:(?P<name1>' + self.settings['varIdentifier'] + ')\s*[:=]\s*)?'
            + 'function(?:\s+(?P<getset>[gs]et))?'
            # function fnName
            + '(?:\s+(?P<name2>' + self.settings['fnIdentifier'] + '))?'
            # (arg1, arg2)
            + '\s*\(\s*(?P<args>.*)\)',
            line
        )
        if not res:
            return None

        name = res.group('name1') and re.sub(self.settings['varIdentifier'], r'\1', res.group('name1')) \
            or res.group('name2') \
            or ''

        args = res.group('args')
        options = {}
        if res.group('getset') == 'set':
            options['as_setter'] = True

        return (name, args, None, options)

    def parseVar(self, line):
        return None

    def getArgName(self, arg):
        return re.sub(self.settings['varIdentifier'] + r'(\s*=.*)?', r'\1', arg)

    def getArgType(self, arg):
        # could actually figure it out easily, but it's not important for the documentation
        return None


class JsdocsObjC(JsdocsParser):

    def setupSettings(self):
        identifier = '[a-zA-Z_$][a-zA-Z_$0-9]*'
        self.settings = {
            # curly brackets around the type information
            "curlyTypes": True,
            'typeInfo': True,
            "typeTag": "type",
            # technically, they can contain all sorts of unicode, but w/e
            "varIdentifier": identifier,
            "fnIdentifier":  identifier,
            "fnOpener": '^\s*[-+]',
            "commentCloser": " */",
            "bool": "Boolean",
            "function": "Function"
        }

    def getDefinition(self, view, pos):
        maxLines = 25  # don't go further than this

        definition = ''
        for i in range(0, maxLines):
            line = read_line(view, pos)
            if line is None:
                break

            pos += len(line) + 1
            # strip comments
            line = re.sub("//.*", "", line)
            if definition == '':
                if not self.settings['fnOpener'] or not re.search(self.settings['fnOpener'], line):
                    definition = line
                    break
            definition += line
            if line.find(';') > -1 or line.find('{') > -1:
                definition = re.sub(r'\s*[;{]\s*$', '', definition)
                break
        return definition

    def parseFunction(self, line):
        # this is terrible, don't judge me

        typeRE = r'[a-zA-Z_$][a-zA-Z0-9_$]*\s*\**'
        res = re.search(
            '[-+]\s+\\(\\s*(?P<retval>' + typeRE + ')\\s*\\)\\s*'
            + '(?P<name>[a-zA-Z_$][a-zA-Z0-9_$]*)'
            # void fnName
            # (arg1, arg2)
            + '\\s*(?::(?P<args>.*))?',
            line
        )
        if not res:
            return
        name = res.group('name')
        argStr = res.group('args')
        args = []
        if argStr:
            groups = re.split('\\s*:\\s*', argStr)
            numGroups = len(groups)
            for i in range(0, numGroups):
                group = groups[i]
                if i < numGroups - 1:
                    result = re.search(r'\s+(\S*)$', group)
                    name += ':' + result.group(1)
                    group = group[:result.start()]

                args.append(group)

            if (numGroups):
                name += ':'
        return (name, '|||'.join(args), res.group('retval'))

    def parseArgs(self, args):
        out = []
        for arg in args.split('|||'):  # lol
            lastParen = arg.rfind(')')
            out.append((arg[1:lastParen], arg[lastParen + 1:]))
        return out

    def getFunctionReturnType(self, name, retval):
        return retval if retval != 'void' and retval != 'IBAction' else None

    def parseVar(self, line):
        return None


class JsdocsJava(JsdocsParser):
    def setupSettings(self):
        identifier = '[a-zA-Z_$][a-zA-Z_$0-9]*'
        self.settings = {
            "curlyTypes": False,
            'typeInfo': False,
            "typeTag": "type",
            "varIdentifier": identifier,
            "fnIdentifier":  identifier,
            "fnOpener": identifier + '(?:\\s+' + identifier + ')?\\s*\\(',
            "commentCloser": " */",
            "bool": "Boolean",
            "function": "Function"
        }

    def parseFunction(self, line):
        line = line.strip()
        res = re.search(
            # Modifiers
            r'(?:(public|protected|private|static|abstract|final|transient|synchronized|native|strictfp)\s+)*'
            # Return value
            + r'(?P<retval>[a-zA-Z_$][<>., a-zA-Z_$0-9]+(\[\])*)\s+'
            # Method name
            + r'(?P<name>' + self.settings['fnIdentifier'] + r')\s*'
            # Params
            + r'\((?P<args>.*)\)\s*'
            # # Throws ,
            + r'(?:throws){0,1}\s*(?P<throws>[a-zA-Z_$0-9\.,\s]*)',
            line
        )

        if not res:
            return None
        group_dict = res.groupdict()
        name = group_dict["name"]
        retval = group_dict["retval"]
        full_args = group_dict["args"]
        throws = group_dict["throws"] or ""

        arg_list = []
        for arg in splitByCommas(full_args):
            arg_list.append(arg.strip().split(" ")[-1])
        args = ",".join(arg_list)

        throws_list = []
        for arg in splitByCommas(throws):
            throws_list.append(arg.strip().split(" ")[-1])
        throws = ",".join(throws_list)

        return (name, args, retval, throws)

    def parseVar(self, line):
        return None

    def guessTypeFromValue(self, val):
        return None

    def formatFunction(self, name, args, retval, throws_args, options={}):
        out = JsdocsParser.formatFunction(self, name, args, retval, options)

        if throws_args != "":
            for unused, exceptionName in self.parseArgs(throws_args):
                typeInfo = self.getTypeInfo(unused, exceptionName)
                out.append("@throws %s%s ${1:[description]}" % (
                    typeInfo,
                    escape(exceptionName)
                ))

        return out

    def getFunctionReturnType(self, name, retval):
        if retval == "void":
            return None
        return retval

    def getDefinition(self, view, pos):
        maxLines = 25  # don't go further than this

        definition = ''
        open_curly_annotation = False
        open_paren_annotation = False
        for i in range(0, maxLines):
            line = read_line(view, pos)
            if line is None:
                break

            pos += len(line) + 1
            # Move past empty lines
            if re.search("^\s*$", line):
                continue
            # strip comments
            line = re.sub("//.*", "", line)
            line = re.sub(r"/\*.*\*/", "", line)
            if definition == '':
                # Must check here for function opener on same line as annotation
                if self.settings['fnOpener'] and re.search(self.settings['fnOpener'], line):
                    pass
                # Handle Annotations
                elif re.search("^\s*@", line):
                    if re.search("{", line) and not re.search("}", line):
                        open_curly_annotation = True
                    if re.search("\(", line) and not re.search("\)", line):
                        open_paren_annotation = True
                    continue
                elif open_curly_annotation:
                    if re.search("}", line):
                        open_curly_annotation = False
                    continue
                elif open_paren_annotation:
                    if re.search("\)", line):
                        open_paren_annotation = False
                elif re.search("^\s*$", line):
                    continue
                # Check for function
                elif not self.settings['fnOpener'] or not re.search(self.settings['fnOpener'], line):
                    definition = line
                    break
            definition += line
            if line.find(';') > -1 or line.find('{') > -1:
                definition = re.sub(r'\s*[;{]\s*$', '', definition)
                break
        return definition

class JsdocsRust(JsdocsParser):
    def setupSettings(self):
        self.settings = {
            "curlyTypes": False,
            'typeInfo': False,
            "typeTag": False,
            "varIdentifier": ".*",
            "fnIdentifier":  ".*",
            "fnOpener": "^\s*fn",
            "commentCloser": " */",
            "bool": "Boolean",
            "function": "Function"
        }

    def parseFunction(self, line):
        res = re.search('\s*fn\s+(?P<name>\S+)', line)
        if not res:
            return None

        name = res.group('name').join('')

        return (name, [])

    def formatFunction(self, name, args):
        return name

############################################################33


class JsdocsIndentCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        v = self.view
        for sel in v.sel():
            currPos = sel.begin()
            currLineRegion = v.line(currPos)
            currCol = currPos - currLineRegion.begin() # the column we’re currently in
            prevLine = v.substr(v.line(v.line(currPos).begin() - 1))
            spaces = self.getIndentSpaces(prevLine)
            if spaces:
                toStar = len(re.search(r'^(\s*\*)', prevLine).group(1))
                toInsert = spaces - currCol + toStar
                if spaces is None or toInsert <= 0:
                    v.run_command(
                        'insert_snippet', {
                            'contents': '\t'
                        }
                    )
                    return

                v.insert(edit, currPos, ' ' * toInsert)
            else:
                v.insert(edit, currPos, '\t')

    def getIndentSpaces(self, line):
        hasTypes = getParser(self.view).settings['typeInfo']
        extraIndent = '\\s+\\S+' if hasTypes else ''
        res = re.search(r'^\s*\*(?P<fromStar>\s*@(?:param|property)%s\s+\S+\s+(?:-\s+)?)\S' % extraIndent, line) \
           or re.search(r'^\s*\*(?P<fromStar>\s*@(?:returns?|define)%s\s+(?:-\s+)?)\S'      % extraIndent, line) \
           or re.search(r'^\s*\*(?P<fromStar>\s*@[a-z]+\s+(?:-\s+)?)\S', line) \
           or re.search(r'^\s*\*(?P<fromStar>\s*(?:-\s+)?)',             line)
        if res:
            return len(res.group('fromStar'))
        return None


class JsdocsJoinCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v = self.view
        for sel in v.sel():
            for lineRegion in reversed(v.lines(sel)):
                joinWith = ' '
                textAtLineBreak = v.substr(v.find(r'\S?[ \t]*\n[ \t]*(?:(?:\*(?!/(?:\s|$))|//[!/]?|#)[ \t]*\S?)?', lineRegion.begin()))

                # If the last char of the line is a hyphen and the next line does _not_ begin with a
                # hyphen, join the lines with no space in-between.
                if textAtLineBreak.startswith('-') and not textAtLineBreak.endswith('-'):
                    joinWith = ''

                v.replace(edit, v.find(r'[ \t]*\n[ \t]*(?:(?:\*(?!/(?:\s|$))|//[!/]?|#)[ \t]*)?', lineRegion.begin()), joinWith)


class JsdocsDecorateCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        v = self.view
        re_whitespace = re.compile("^(\\s*)//")
        v.run_command('expand_selection', {'to': 'scope'})
        for sel in v.sel():
            maxLength = 0
            lines = v.lines(sel)
            for lineRegion in lines:
                lineText = v.substr(lineRegion)
                tabCount = lineText.count("\t")
                leadingWS = len(re_whitespace.match(lineText).group(1))
                leadingWS = leadingWS - tabCount
                maxLength = max(maxLength, lineRegion.size())

            lineLength = maxLength - (leadingWS + tabCount)
            leadingWS = tabCount * "\t" + " " * leadingWS
            v.insert(edit, sel.end(), leadingWS + "/" * (lineLength + 3) + "\n")

            for lineRegion in reversed(lines):
                line = v.substr(lineRegion)
                rPadding = 1 + (maxLength - lineRegion.size())
                v.replace(edit, lineRegion, leadingWS + line + (" " * rPadding) + "//")
                # break

            v.insert(edit, sel.begin(), "/" * (lineLength + 3) + "\n")


class JsdocsDeindent(sublime_plugin.TextCommand):
    """
    When pressing enter at the end of a docblock, this takes the cursor back one space.
    /**
     *
     */|   <-- from here
    |      <-- to here
    """
    def run(self, edit):
        v = self.view
        lineRegion = v.line(v.sel()[0])
        line = v.substr(lineRegion)
        v.insert(edit, v.sel()[0].begin(), re.sub("^(\\s*)\\s\\*/.*", "\n\\1", line))


class JsdocsReparse(sublime_plugin.TextCommand):
    """
    Reparse a docblock to make the fields 'active' again, so that pressing tab will jump to the next one
    """
    def run(self, edit):
        tabIndex = counter()

        def tabStop(match):
            return "${%d:%s}" % (next(tabIndex), match.group(1))

        v = self.view
        v.run_command('clear_fields')
        sel = getDocBlockRegion(v, v.sel()[0].begin())

        # Remove the newline at the end of the region.
        sel = sublime.Region(sel.begin(), sel.end() - 1)

        # escape string, so variables starting with $ won't be removed
        text = escape(v.substr(sel))

        # strip out leading spaces, since inserting a snippet keeps the indentation
        text = re.sub(r'\n\s+\*', '\n *', text)

        # replace [bracketed] [text] with a tabstop
        text = re.sub(r'(\[.+?\])', tabStop, text)

        v.erase(edit, sel)
        write(v, text)


class JsdocsTrimAutoWhitespace(sublime_plugin.TextCommand):
    """
    Trim the automatic whitespace added when creating a new line in a docblock.
    """
    def run(self, edit):
        v = self.view
        lineRegion = v.line(v.sel()[0])
        line = v.substr(lineRegion)
        spaces = max(0, v.settings().get("jsdocs_indentation_spaces", 1))
        v.replace(edit, lineRegion, re.sub("^(\\s*\\*)\\s*$", "\\1\n\\1" + (" " * spaces), line))


class JsdocsWrapLinesOld(sublime_plugin.TextCommand):
    """
    Reformat description text inside a comment block to wrap at the correct length.
    Wrap column is set by the first ruler (set in Default.sublime-settings), or 80 by default.
    Shortcut Key: alt+q
    """
    def run(self, edit):
        v = self.view
        settings = v.settings()
        rulers = settings.get('rulers')
        tabSize = settings.get('tab_size')

        wrapLength = rulers[0] if (len(rulers) > 0) else 80
        numIndentSpaces = max(0, settings.get("jsdocs_indentation_spaces", 1))
        indentSpaces = " " * numIndentSpaces
        numIndentSpacesSamePara = settings.get("jsdocs_indentation_spaces_same_para", numIndentSpaces)
        indentSpacesSamePara = " " * max(0, numIndentSpacesSamePara) if type(numIndentSpaces) is type(int()) else numIndentSpacesSamePara
        spacerBetweenSections = settings.get("jsdocs_spacer_between_sections") == True
        spacerBetweenDescriptionAndTags = settings.get("jsdocs_spacer_between_sections") == "after_description"

        dbRegion = getDocBlockRegion(v, v.sel()[0].begin())

        # find the first word
        startPoint = v.find(r'/\*\*\s*', dbRegion.begin()).end()
        # find the first tag, or the end of the comment
        endPoint = v.find(r'\s*\n\s*\*(/)', dbRegion.begin()).begin()

        # replace the selection with this ^ new selection
        v.sel().clear()
        v.sel().add(sublime.Region(startPoint, endPoint))
        # get the description text
        text = v.substr(v.sel()[0])

        # find the indentation level
        indentation = len(re.sub('\t', ' ' * tabSize, re.search(r'\n(\s*\*)', text).group(1)))
        wrapLength -= indentation - tabSize

        # join all the lines, collapsing "empty" lines
        text = re.sub(r'\n(\s*\*\s*\n)+', '\n\n', text)

        def wrapPara(para):
            para = re.sub(r'(\n|^)\s*\*\s*', ' ', para)

            # split the paragraph into words
            words = para.strip().split(' ')
            text = '\n'
            line = ' *' + indentSpaces
            lineTagged = False  # indicates if the line contains a doc tag
            paraTagged = False  # indicates if this paragraph contains a doc tag
            lineIsNew = True
            tag = ''

            # join all words to create lines, no longer than wrapLength
            for i, word in enumerate(words):
                if not word and not lineTagged:
                    continue

                if lineIsNew and word[0] == '@':
                    lineTagged = True
                    paraTagged = True
                    tag = word

                if len(line) + len(word) >= wrapLength - 1:
                    # appending the word to the current line would exceed its
                    # length requirements
                    text += line.rstrip() + '\n'
                    line = ' *' + indentSpacesSamePara + word + ' '
                    lineTagged = False
                    lineIsNew = True
                else:
                    line += word + ' '

                lineIsNew = False

            text += line.rstrip()
            return {
                'text'       : text,
                'lineTagged' : lineTagged,
                'tagged'     : paraTagged,
                'tag'        : tag
            }

        # split the text into paragraphs, where each paragraph is either
        # defined by an empty line or the start of a doc parameter
        paragraphs = re.split(r'\n{2,}|\n\s*\*\s*(?=@)', text)
        wrappedParas = []
        text = ''

        for para in paragraphs:
            if para[0] == '@':
                para = re.sub(r'\n[ \t]+\*[ \t]+(?!@)', ' ', para)
            # wrap the lines in the current paragraph
            wrappedParas.append(wrapPara(para))

        lastParaIndex = len(wrappedParas) - 1

        # combine all the paragraphs into a single piece of text
        for i, para in enumerate(wrappedParas):
            last = i == lastParaIndex

            nextIsTagged = not last and wrappedParas[i + 1]['tagged']
            nextIsSameTag = nextIsTagged and para['tag'] == wrappedParas[i + 1]['tag']

            if last or (para['lineTagged'] or nextIsTagged) and \
                    not (spacerBetweenSections and not nextIsSameTag) and \
                    not (not para['lineTagged'] and nextIsTagged and spacerBetweenDescriptionAndTags):
                text += para['text']
            else:
                text += para['text'] + '\n *'

        text = escape(text)
        write(v, text)


class JsdocsWrapLines(sublime_plugin.TextCommand):
    """
    Reformat description text inside a comment block to wrap at the correct length.
    Wrap column is set by the first ruler (set in Default.sublime-settings), or 80 by default.
    Shortcut Key: alt+q
    """
    def run(self, edit):
        v = self.view
        settings = v.settings()
        rulers = settings.get('rulers')
        tabSize = sublime.load_settings('Preferences.sublime-settings').get('tab_size')

        wrapLength = rulers[0] if len(rulers) > 0 else 80
        columnSpacesCount = settings.get('jsdocs_min_spaces_between_columns', 1)
        columnSpaces      = (' ' * columnSpacesCount)
        docIndentSpacesCount = max(0, settings.get('jsdocs_indentation_spaces', 1))
        docIndent            = (' ' * docIndentSpacesCount)
        deepIndentWrappedLines = settings.get('jsdocs_deep_indent')
        paragraphIndentSpacesCount = settings.get('jsdocs_indentation_spaces_same_para', docIndentSpacesCount)
        paragraphIndent            = (' ' * max(0, paragraphIndentSpacesCount)) if type(paragraphIndentSpacesCount) is type(int()) else paragraphIndentSpacesCount
        spacerBetweenSections           = settings.get('jsdocs_spacer_between_sections') == True
        spacerBetweenDescriptionAndTags = settings.get('jsdocs_spacer_between_sections') == 'after_description'
        dashBeforeDescription = settings.get('jsdocs_dash_before_description')
        descriptionSeparator = ('-' + columnSpaces) if dashBeforeDescription else ''
        descriptionSeparatorLength = len(descriptionSeparator)
        descriptionSeparatorPlaceholder = '§' * descriptionSeparatorLength
        alignTags = settings.get('jsdocs_align_tags', False)
        alignTagsExcludeList = settings.get('jsdocs_align_tags_exclude', [])

        if type(alignTags) != bool:
            alignTags = True if alignTags in {'shallow', 'deep'} else False

        dbRegion = getDocBlockRegion(v, v.sel()[0].begin())
        originalLineCount = len(v.lines(dbRegion))

        # find the first character that is not whitespace, a slash or an asterisk
        startPoint = v.find(r'/\*\*', dbRegion.begin()).end()
        # find the end of the comment
        endPoint = v.find(r'\*/', dbRegion.begin()).begin()

        # Determine the doc’s region.
        docRegion = sublime.Region(startPoint, endPoint)
        # replace the selection with this ^ new selection
        v.sel().clear()
        v.sel().add(docRegion)
        # Get the doc text.
        text = v.substr(docRegion)

        # find the indentation level
        if originalLineCount == 1:
            indent = re.search(r'^.*?(?=/\*\*)', v.substr(v.line(dbRegion.begin()))).group(0)
            lineStart = indent + '/**'
        else:
            indent = re.search(r'^\s*', v.substr(v.line(dbRegion.begin()))).group(0)
            lineStart = indent + ' *' + docIndent
        lineStartLength = len(re.sub(r'\t', ' ' * tabSize, lineStart))
        wrapLength -= lineStartLength
        #print('  - indent:     "' + indent + '"') # DEBUG
        #print('  - line start: "' + lineStart + '"') # DEBUG
        #print('  - line start length:', lineStartLength) # DEBUG
        #print('  - wrap length:', wrapLength) # DEBUG

        def trimBlankLines(out):
            while len(out) and out[0] is '':
                out = out[1:]
            while len(out) and out[-1] is '':
                out = out[:-1]
            return out

        lines = trimBlankLines(text.split('\n'))
        context = ''
        paragraph = ''
        inCodeBlock  = False
        inListItem   = False
        inBlockquote = False
        inExampleTag = False
        listIndent       = ''
        blockquoteIndent = ''
        out = []
        tags = []
        tagColumnWidths = []

        lineType     = ''
        prevLineType = ''
        nextLineType = ''
        docLinePrefix = re.compile(r'^\s*\* {,' + str(docIndentSpacesCount) + '}')

        def addLine(lineToAdd):
            nonlocal paragraph
            strippedParagraph = paragraph.strip()
            strippedLine = lineToAdd.strip()
            #if paragraph.strip() and strippedLine and not getMatch(r'-\w', strippedLine):
            if strippedParagraph and strippedLine:
                if strippedParagraph.endswith('-') and not strippedLine.startswith('-'):
                    paragraph = paragraph.rstrip() + lineToAdd
                else:
                    paragraph += (' ' + lineToAdd)
                return
            paragraph += lineToAdd

        def addParagraph(paragraphToAdd, force=False):
            nonlocal docIndent
            nonlocal tags
            nonlocal out
            nonlocal wrapLength
            nonlocal paragraph
            nonlocal context
            nonlocal inListItem
            nonlocal listIndent
            nonlocal inBlockquote
            nonlocal blockquoteIndent
            indent = docIndent
            paragraphToAddType = getLineType(paragraphToAdd)
            if inListItem and paragraphToAddType not in {'LIST', 'LIST ORDERED'}:
                indent += listIndent
            if inBlockquote and paragraphToAddType is not 'BLOCKQUOTE':
                indent += blockquoteIndent
            if paragraphToAdd.strip() or force:
                if context == 'tags':
                    tags.append(splitTag(paragraphToAdd))
                elif len((indent + paragraphToAdd).rstrip()) > wrapLength + 1:
                    out += wrapDoc(indent, paragraphToAdd, False)
                else:
                    out.append((indent + paragraphToAdd).rstrip())
                #print('> ¶' + paragraphToAdd) # DEBUG
            paragraph = ''

        def splitTag(tagParagraph):
            nonlocal tagColumnWidths
            parsedTag = parseJSDocTag(tagParagraph)
            tagParts = list(parsedTag or (tagParagraph,))
            #print('PARTS', tagParts) # DEBUG
            if parsedTag and (tagParts[0] not in alignTagsExcludeList):
                for i, tagPart in enumerate(tagParts):
                    # Add another item to the tag-column-widths list if necessary.
                    if i == len(tagColumnWidths):
                        tagColumnWidths += [0]
                    # Set the width of the column to this tag-part’s width (if it’s larger).
                    tagColumnWidths[i] = max(tagColumnWidths[i], len(tagPart))
                #print('    · TAG COLUMN WIDTHS:', tagColumnWidths) # DEBUG
            #elif parsedTag: # DEBUG
                #print('    · TAG EXCLUDED FROM ALIGNMENT') # DEBUG
            return tagParts

        def splitMarkdownParagraph(text):
            return re.findall(r'(?<=[^a-zA-Z0-9])(?:`(?=\S).*?\S`|{@link \S*})(?=[^a-zA-Z0-9])\S*|\S*\[(?=\S).*?\S\]\(\S*?\)\S*|\S+', text)

        def wrapDoc(currentText, remainingText, indent=True):
            nonlocal columnSpacesCount
            nonlocal docIndent
            nonlocal docIndentSpacesCount
            nonlocal paragraphIndentSpacesCount
            nonlocal paragraphIndent
            nonlocal wrapLength
            nonlocal descriptionSeparator
            nonlocal descriptionSeparatorLength
            nonlocal inListItem
            nonlocal listIndent
            nonlocal inBlockquote
            nonlocal blockquoteIndent
            lines = []
            #print('WRAP ----------------------------') # DEBUG
            if ' ' in remainingText:
                #print('    · LINE HAS WORDS') # DEBUG
                words = splitMarkdownParagraph(remainingText)
                # Determine the amount of indent that the paragraph should have.
                if paragraphIndentSpacesCount == 'auto' or deepIndentWrappedLines:
                    paragraphIndent = (' ' * (len(currentText) - docIndentSpacesCount + descriptionSeparatorLength))
                # Wrap.
                for i, word in enumerate(words):
                    #print(currentText) # DEBUG
                    # If the next word would put us over the limit, wrap.
                    if len(currentText + word) > wrapLength + 1:
                        # If there’s a hyphen in the word and the word is not one of the following:
                        #
                        # - a Markdown code span
                        # - a Markdown link
                        # - a JSDoc inline link
                        # - a word starting with a dash (<-- is this actually handled??)
                        # - two or more hyphens suggesting an en-/em-dash
                        #
                        # then try breaking the word at each hyphen and continuing to add to the
                        # line until over the limit.
                        if '-' in word and word[0] not in {'`', '[', '{'} and not re.match(r'^-{2,}$', word):
                            subwords = re.findall(r'-*[^-]+-*', word)

                            while len(currentText + subwords[0]) <= wrapLength + 1:
                                currentText += subwords.pop(0)

                            # Set `word` to be whatever’s left over from the word.
                            word = ''.join(subwords)

                        #print('--WRAP') # DEBUG
                        lines.append(currentText.rstrip())
                        if indent:
                            #print('----INDENT') # DEBUG
                            currentText = docIndent + paragraphIndent
                        elif inListItem:
                            #print('----IN LIST') # DEBUG
                            currentText = docIndent + listIndent
                        elif inBlockquote:
                            #print('----IN BLOCKQUOTE') # DEBUG
                            currentText = docIndent + blockquoteIndent
                        else:
                            currentText = docIndent
                        #print(currentText) # DEBUG
                    # Add the word to the output.
                    currentText += word + ' '
                else:
                    #print(currentText) # DEBUG
                    lines.append(currentText.rstrip())
            else:
                lines.append(currentText.rstrip())
                currentText = docIndent
                # If the next part would _still_ put us over the limit, add it anyway (rare).
                if len(currentText + remainingText) > wrapLength + 1:
                    if indent:
                        lines.append(currentText + paragraphIndent + remainingText)
                    else:
                        lines.append(currentText + remainingText)
                    currentText = docIndent
            return lines

        def getLineType(line):
            lineType = ''
            if line.strip() is '':
                lineType = 'EMPTY'
            #elif getMatch(re.compile(docIndent + '    '), line):
            #    lineType = 'code indented'
            elif getMatch(r'^[ \t]*@\w+(?=\s|$)', line):
                lineType = 'TAG'
            elif getMatch(r'^[ \t]*#+\s+\S', line):
                lineType = 'HEADING'
            elif getMatch(r'^[ \t]*[*+-]\s+', line):
                lineType = 'LIST'
            elif getMatch(r'^[ \t]*\d+\.\s+', line):
                lineType = 'LIST ORDERED'
            elif getMatch(r'^[ \t]*````*[\w+-]*\s*$', line):
                lineType = 'CODE'
            elif getMatch(r'^[ \t]*>+\s+\S', line):
                lineType = 'BLOCKQUOTE'
            elif getMatch(r'^[ \t]*([^a-zA-Z0-9]*[a-zA-Z0-9]|`[^`]+`)', line): # code spans are text
                lineType = 'TEXT'
            else:
                lineType = 'SYMBOLS'
            return lineType

        for i, line in enumerate(lines):
            prevLine = re.sub(docLinePrefix, '', lines[i - 1]) if i > 0 else None
            lineRaw  = re.sub(docLinePrefix, '', line)
            nextLine = re.sub(docLinePrefix, '', lines[i + 1]) if i < len(lines) - 1 else None

            line = lineRaw.strip()

            prevLineType    = lineType
            currentLineType = nextLineType or getLineType(line)
            nextLineType    = getLineType(nextLine) if nextLine != None else None

            # ·→
            #print('[' + currentLineType + ']', line) # DEBUG
            #if line != lineRaw: # DEBUG
                #print(' (RAW)', lineRaw) # DEBUG

            # IF this IS the first line AND it IS NOT a tag-line
                # current-context is 'description'
            if i == 0 and currentLineType != 'TAG':
                context = 'description'

            # IF IN example
                # add raw line to paragraph
                # add paragraph
                # IF next-line IS tag
                    # exit example
                # CONTINUE
            if inExampleTag:
                addLine(lineRaw) # preserve leading whitespace
                addParagraph(paragraph, True) # preserve empty lines
                if nextLineType == 'TAG':
                    inExampleTag = False
                continue

            # IF current-line IS fenced-code
                # IF IN fenced-code
                    # add raw line to paragraph
                    # add paragraph
                    # exit fenced-code
                    # CONTINUE
                # enter fenced-code
            # IF IN fenced-code
                # add raw line to paragraph
                # add paragraph
                # CONTINUE
            if currentLineType == 'CODE':
                if inCodeBlock:
                    addLine(lineRaw) # preserve leading whitespace
                    addParagraph(paragraph, True) # preserve empty lines
                    inCodeBlock = False
                    continue
                inCodeBlock = True
            if inCodeBlock:
                addLine(lineRaw) # preserve leading whitespace
                addParagraph(paragraph, True) # preserve empty lines
                continue

            # IF current-line IS list-item
                # add paragraph
                # IF NOT IN list
                    # enter list
                    # cache indent
            # IF IN list
                # IF current-line IS list-item
                    # add raw line to paragraph
                # ELSE
                    # add line to paragraph
                # IF current-line IS empty
                    # add paragraph
                    # IF next-line IS NOT empty
                        # add empty paragraph
                        # IF next-line IS text and does NOT have list indent
                            # exit list
                            # uncache indent
                # IF next-line IS NOT empty/text AND does NOT have list indent
                    # add paragraph
                    # exit list
                    # uncache indent
                # CONTINUE
            if currentLineType in {'LIST', 'LIST ORDERED'}:
                addParagraph(paragraph)
                if not inListItem:
                    inListItem = True
                listIndent = (' ' * len(getMatch(r'^[ \t]*(?:\d+\.|\*|\+|-)\s+', lineRaw)))
                #print('INDENT "' + listIndent + '"') # DEBUG
            if inListItem:
                if currentLineType in {'LIST', 'LIST ORDERED'}:
                    addLine(lineRaw.rstrip())
                else:
                    addLine(line)
                #print('   "' + paragraph + '"') # DEBUG
                nextLineIsIndented = nextLine and getMatch(listIndent, nextLine)
                if currentLineType == 'EMPTY':
                    addParagraph(paragraph) # end/add the current ¶
                    if nextLineType != 'EMPTY':
                        addParagraph('', True) # add empty ¶ now that the next line won’t be empty
                        if nextLineType == 'TEXT' and not nextLineIsIndented:
                            inListItem = False
                            listIndent = ''
                if nextLineType not in {'EMPTY', 'TEXT'} and not nextLineIsIndented:
                    addParagraph(paragraph)
                    inListItem = False
                    listIndent = ''
                continue

            # IF current-line IS blockquote
                # add paragraph
                # IF NOT IN blockquote
                    # enter blockquote
                    # cache indent
            # IF IN blockquote
                # IF current-line IS blockquote
                    # add raw line to paragraph
                # ELSE
                    # add line to paragraph
                # IF current-line IS empty
                    # add paragraph
                    # IF next-line IS NOT empty
                        # add empty paragraph
                        # IF next-line IS text and does NOT have blockquote indent
                            # exit blockquote
                            # uncache indent
                # IF next-line IS NOT empty/text AND does NOT have blockquote indent
                    # add paragraph
                    # exit blockquote
                    # uncache indent
                # CONTINUE
            if currentLineType == 'BLOCKQUOTE':
                addParagraph(paragraph)
                if not inBlockquote:
                    inBlockquote = True
                blockquoteIndent = (' ' * len(getMatch(r'^[ \t]*>\s+', lineRaw)))
                #print('INDENT "' + blockquoteIndent + '"') # DEBUG
            if inBlockquote:
                if currentLineType == 'BLOCKQUOTE':
                    addLine(lineRaw.rstrip())
                else:
                    addLine(line)
                #print('"' + paragraph + '"') # DEBUG
                nextLineIsIndented = nextLine and getMatch(blockquoteIndent, nextLine)
                if currentLineType == 'EMPTY':
                    addParagraph(paragraph) # end/add the current ¶
                    if nextLineType != 'EMPTY':
                        addParagraph('', True) # add empty ¶ now that the next line won’t be empty
                        if nextLineType == 'TEXT' and not nextLineIsIndented:
                            inBlockquote = False
                            blockquoteIndent = ''
                if nextLineType not in {'EMPTY', 'TEXT'} and not nextLineIsIndented:
                    addParagraph(paragraph)
                    inBlockquote = False
                    blockquoteIndent = ''
                continue

            # IF current-line IS tag
                # set context (exit description)
                # add paragraph
                # add line to paragraph
                # IF tag IS @example
                    # add paragraph
                    # enter example
                # CONTINUE
            # IF current-context IS tags
                # IF next-line IS indented-code
                    # change next-line type to 'text'
            if currentLineType == 'TAG':
                context = 'tags'
                addParagraph(paragraph)
                addLine(line)
                if line.startswith('@example'):
                    #print('    · EXAMPLE TAG') # DEBUG
                    addParagraph(paragraph)
                    inExampleTag = True
                continue

            # IF current-line IS empty
                # add paragraph
                # IF current-context IS NOT tags
                    # add empty paragraph
                # CONTINUE
            if currentLineType == 'EMPTY':
                addParagraph(paragraph)
                # Only preserve blank lines for the description (don’t include in the tags section).
                if context == 'description':
                    addParagraph('', True)
                continue

            # IF current-line IS text
                # IF next-line IS text
                    # add line to paragraph
                # ELSE IF next-line IS {empty, blockquote, list-item, fenced-code, tag}
                    # add line to paragraph
                    # add paragraph
                # CONTINUE
            if currentLineType == 'TEXT':
                if nextLineType == 'TEXT' or nextLine == None:
                    addLine(line)
                elif nextLineType in {'EMPTY', 'BLOCKQUOTE', 'LIST', 'LIST ORDERED', 'CODE', 'TAG', 'SYMBOLS'}:
                    addLine(line)
                    addParagraph(paragraph)
                continue

            ## IF current-line IS blockquote
            #    # IF next-line IS blockquote
            #        # add line to paragraph
            #    # IF next-line IS {empty, blockquote, list-item, fenced-code, tag}
            #        # add line to paragraph
            #        # add paragraph
            #    # CONTINUE
            #if currentLineType == 'BLOCKQUOTE':
            #    if nextLineType == 'BLOCKQUOTE':
            #        addLine(line)
            #    elif nextLineType in {'EMPTY', 'LIST', 'LIST ORDERED', 'CODE', 'TAG'}:
            #        addLine(line)
            #        addParagraph(paragraph)
            #    continue

            addParagraph(paragraph)
            addLine(lineRaw.rstrip())
            addParagraph(paragraph)
        else:
           addParagraph(paragraph)

        out = trimBlankLines(out)

        if spacerBetweenDescriptionAndTags and len(out) and len(tags):
            out.append('')

        #print('\nCOLUMN WIDTHS:', tagColumnWidths) # DEBUG
        #print('\nWRAP TAGS -----------------------') # DEBUG
        #print('    · NO ALIGN' if not alignTags else '    · ALIGN') # DEBUG

        # Wrap Tag Parts
        for tagParts in tags:
            tagPartsLength = len(tagParts)
            excludeTagFromAlignment = tagParts[0] in alignTagsExcludeList
            tagOut = docIndent

            #print('\nPARTS:', tagParts) # DEBUG
            #if alignTags and excludeTagFromAlignment: # DEBUG
                #print('--EXCLUDE TAG FROM ALIGNMENT') # DEBUG

            if tagPartsLength == 1:
                out.append((tagOut + tagParts[0]).rstrip())
                continue

            for ii, tagPart in enumerate(tagParts):
                # If the next part would put us over the limit, wrap it.
                isTagPartDescription = (ii == tagPartsLength - 1) and ' ' in tagPart
                addDescriptionSeparator = isTagPartDescription and descriptionSeparator
                #if isTagPartDescription: # DEBUG
                    #print('--PART IS DESCRIPTION') # DEBUG

                # If tags description should be separated with a dash, add a placeholder separator
                # to the beginning of the first word of the description so that the wrapping will be
                # calculated correctly.
                if addDescriptionSeparator:
                    tagPart = re.sub(r'^ *- *', descriptionSeparatorPlaceholder, tagPart)
                    #print('    · ADD TEMP SEPARATOR:', tagPart) # DEBUG
                else:
                    tagPart = re.sub(r'^ *- *', '', tagPart)

                # Check if adding the tag part as-is would cause us to go over the wrap limit.
                if len(tagOut + tagPart) > wrapLength + 1:
                    wrappedTag = wrapDoc(tagOut, tagPart)
                    # Swap the placeholder description separator for the real separator.
                    if addDescriptionSeparator:
                        wrappedTag[0] = wrappedTag[0].replace(descriptionSeparatorPlaceholder, descriptionSeparator)
                        #print('    · ADD REAL SEPARATOR:', wrappedTag[0]) # DEBUG
                    out += wrappedTag
                    # Reset `tagOut`.
                    tagOut = docIndent
                    continue

                # Swap the placeholder description separator for the real separator.
                if addDescriptionSeparator:
                    tagPart = tagPart.replace(descriptionSeparatorPlaceholder, descriptionSeparator)
                    #print('    · ADD REAL SEPARATOR:', tagPart) # DEBUG

                # Add the tag part (optionally aligned).
                if alignTags and not excludeTagFromAlignment:
                    # Pad the string on the right with spaces so that the next bit of text will be
                    # aligned with the next column.
                    tagOut += tagPart.ljust(tagColumnWidths[ii] + columnSpacesCount)
                else:
                    tagOut += tagPart + columnSpaces

                #print('|' + tagOut + '|') # DEBUG

            if tagOut != docIndent:
                out.append(tagOut.rstrip())

        #print('\nPARAGRAPHS:\n', out) # DEBUG

        if originalLineCount == 1:
            if len(out) == 1:
                out = out[0] + docIndent
            else:
                lineStart = '\n' + (' ' * (lineStartLength - 3)) + ' *'
                out = lineStart + lineStart.join(out) + lineStart[:-1]
        else:
            out = '\n *' + '\n *'.join(out) + '\n '

        #print(out)
        #out = escape(out)
        #return
        #v.replace(edit, docRegion, out)
        write(v, out)


class JsdocsFoldCommand(sublime_plugin.TextCommand):
    """
    Fold a doc block.
    Shortcut Key: super+alt+[
    """

    def run(self, edit):
        view = self.view

        docBlockRegion = getDocBlockRegion(view, view.sel()[0].begin())

        # find the first character that is not whitespace, a slash or an asterisk
        startPoint = view.find(r'/\*\*', docBlockRegion.begin()).end()
        # find the end of the comment
        endPoint = view.find(r'\*/', docBlockRegion.begin()).begin()

        # Determine the doc’s region.
        docRegion = sublime.Region(startPoint, endPoint)

        view.fold(docRegion)



class JsdocsTypescript(JsdocsParser):

    def setupSettings(self):
        identifier = '[a-zA-Z_$][a-zA-Z_$0-9]*'
        base_type_identifier = r'%s(\.%s)*(\[\])?' % ((identifier, ) * 2)
        parametric_type_identifier = r'%s(\s*<\s*%s(\s*,\s*%s\s*)*>)?' % ((base_type_identifier, ) * 3)
        self.settings = {
            # curly brackets around the type information
            "curlyTypes": True,
            'typeInfo': True,
            "typeTag": "type",
            # technically, they can contain all sorts of unicode, but w/e
            "varIdentifier": identifier,
            "fnIdentifier": identifier,
            "fnOpener": 'function(?:\\s+' + identifier + ')?\\s*\\(',
            "commentCloser": " */",
            "bool": "Boolean",
            "function": "Function",
            "functionRE":
                # Modifiers
                r'(?:public|private|static)?\s*'
                # Method name
                + r'(?P<name>' + identifier + r')\s*'
                # Params
                + r'\((?P<args>.*)\)\s*'
                # Return value
                + r'(:\s*(?P<retval>' + parametric_type_identifier + r'))?',
            "varRE":
                r'((public|private|static|var)\s+)?(?P<name>' + identifier
                + r')\s*(:\s*(?P<type>' + parametric_type_identifier
                + r'))?(\s*=\s*(?P<val>.*?))?([;,]|$)'
        }
        self.functionRE = re.compile(self.settings['functionRE'])
        self.varRE = re.compile(self.settings['varRE'])

    def parseFunction(self, line):
        line = line.strip()
        res = self.functionRE.search(line)

        if not res:
            return None
        group_dict = res.groupdict()
        return (group_dict["name"], group_dict["args"], group_dict["retval"])

    def getArgType(self, arg):
        if ':' in arg:
            return arg.split(':')[-1].strip()
        return None

    def getArgName(self, arg):
        if ':' in arg:
            arg = arg.split(':')[0]
        return arg.strip('[ \?]')

    def parseVar(self, line):
        res = self.varRE.search(line)
        if not res:
            return None
        val = res.group('val')
        if val: val = val.strip()
        return (res.group('name'), val, res.group('type'))

    def getFunctionReturnType(self, name, retval):
        return retval if retval != 'void' else None

    def guessTypeFromValue(self, val):
        lowerPrimitives = self.viewSettings.get('jsdocs_lower_case_primitives') or False
        if is_numeric(val):
            return "number" if lowerPrimitives else "Number"
        if val[0] == '"' or val[0] == "'":
            return "string" if lowerPrimitives else "String"
        if val[0] == '[':
            return "Array"
        if val[0] == '{':
            return "Object"
        if val == 'true' or val == 'false':
            return "boolean" if lowerPrimitives else "Boolean"
        if re.match('RegExp\\b|\\/[^\\/]', val):
            return 'RegExp'
        if val[:4] == 'new ':
            res = re.search('new (' + self.settings['fnIdentifier'] + ')', val)
            return res and res.group(1) or None
        return None
