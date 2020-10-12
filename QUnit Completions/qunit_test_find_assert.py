import sublime
import sublime_plugin
#import re



PLUGIN_STATUS_KEY = 'qunit_test_find_assert'

OPEN_GROUP_CHARS  = '({['
CLOSE_GROUP_CHARS = ')}]'
STRING_CHARS = '"\'`'


def is_match(str, regex):
    match = regex.match(str)

    if match:
        return match.group(0)
    else:
        return None


def get_start_point(point_or_region):
    if isinstance(point_or_region, int):
        return point_or_region
    else:
        return point_or_region.begin()


def region_is_first(view, region):
    return region.begin() == 0


def region_is_last(view, region):
    return region.end() >= view.size()


def region_for(point_or_region):
    if isinstance(point_or_region, int):
        return sublime.Region(point_or_region)
    else:
        return sublime.Region(point_or_region.begin(), point_or_region.end())


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


def get_prev_char(view, point_or_region):
    region = region_for(point_or_region)
    return view.substr(region.begin() - 1)


def get_prev_char_region(view, point_or_region):
    point = get_start_point(point_or_region)
    return sublime.Region(point - 1)


# def get_prev_char_info(view, point_or_region):
#     point = get_start_point(point_or_region)
#     region = sublime.Region(point - 1)

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


def is_escaped(view, point):
    return get_prev_char(view, point) == '\\'



class QunitTestFindAssertCommand(sublime_plugin.TextCommand):

    clear_status_timeout_id = -1

    def run(self, edit):
        view = self.view

        # [Sanity Check] Only trigger within JS scopes.
        if not view.match_selector(view.sel()[0].begin(), 'source.js'):
            view.set_status(PLUGIN_STATUS_KEY, 'VIEW IS NOT JS')
            self.clear_status_after_delay()
            return

        if not self.is_after_assert(view, view.sel()[0].begin()):
            view.set_status(PLUGIN_STATUS_KEY, 'NO ASSERT')
            self.clear_status_after_delay()


    def is_after_assert(self, view, location):
        # is_assert = False
        inside_group_count = 0

        char_index = location - 1
        char = view.substr(char_index)
        open_group_chars_to_match = []

        while True:
            # print(char_index, char) # DEBUG
            open_group_char_index = OPEN_GROUP_CHARS.find(char)
            close_group_char_index = CLOSE_GROUP_CHARS.find(char)

            if open_group_char_index > -1 and not is_escaped(view, char_index):
                # If we’re not in a group but we have an open group char then quit, because we’ve
                # reached the beginning of the containing block.
                if inside_group_count == 0:
                    # print('  CHAR IS BEGINNING OF CONTAINING BLOCK') # DEBUG
                    return False
                # If we’re in a group but the open-group-char doesn’t match then there’s a syntax
                # error and we can quit.
                if char != open_group_chars_to_match[-1]:
                    # print('  CHAR DOESN’T MATCH, THERE MUST BE AN ERROR') # DEBUG
                    return False
                # print('  CHAR CLOSES GROUP', inside_group_count) # DEBUG
                inside_group_count -= 1
                open_group_chars_to_match.pop()
            elif view.match_selector(char_index, 'string, comment, regex, regexp'):
                # print('  CHAR IS PART OF STRING, COMMENT OR REGEX') # DEBUG
                ignore_region = expand_to_scope(view, char_index, 'string, comment, regex, regexp')
                char_index = ignore_region.begin()
                # print('  ', view.substr(ignore_region)) # DEBUG
                # print('  SKIP TO', char_index) # DEBUG
            elif close_group_char_index > -1 and not is_escaped(view, char_index):
                open_group_chars_to_match.append(OPEN_GROUP_CHARS[close_group_char_index])
                inside_group_count += 1
                # print('  CHAR OPENS GROUP ', inside_group_count) # DEBUG
            elif view.match_selector(char_index, 'support.module.node, variable - variable.function'):
                # print('  FOUND MATCHING SCOPE') # DEBUG
                token_region = expand_to_scope(view, char_index, 'support.module.node, variable')
                if view.substr(token_region) == 'assert' and inside_group_count == 0:
                    view.sel().subtract(view.sel()[0])
                    view.sel().add(token_region)
                    # print('  FOUND `assert`!') # DEBUG
                    return True
                # print('  QUIT SINCE TOKEN `%s` IS NOT `assert`' % view.substr(token_region)) # DEBUG
                return False

            char_index -= 1
            char = view.substr(char_index)

            if char_index < 0:
                return False


    def clear_status_after_delay(self):
        self.clear_status_timeout_id += 1
        timeout_id = self.clear_status_timeout_id

        sublime.set_timeout_async(lambda: timeout_id is self.clear_status_timeout_id and self.view.erase_status(PLUGIN_STATUS_KEY), 3000)
