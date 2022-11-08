"""A parser for HTML templates.

This file is based on Lib/html/parser.py (https://github.com/python/cpython/tree/3.10/Lib/html/parser.py)

This a modified version of python's html.parser library, expanded to handle
html templates.

See Python's license: https://github.com/python/cpython/blob/main/LICENSE


- convert_charrefs option is always True.
- feed cannot be passed a single char, but a full string

"""
# pylint: disable=R0913

import re
from html import unescape

import _markupbase

__all__ = ["Htp"]

_declname_match = re.compile(r"[a-zA-Z][-_.a-zA-Z0-9]*\s*").match
_declstringlit_match = re.compile(r'(\'[^\']*\'|"[^"]*")\s*').match
_commentclose = re.compile(r"--\s*>")
_commentclosecurlyhash = re.compile(r"#}")
_commentclosecurlyperc = re.compile(r"{%\s*endcomment\s*%}")
_commentclosecurlycurlyexlaim = re.compile(r"}}")
_commentcloseatstar = re.compile(r"\*@")
_markedsectionclose = re.compile(r"]\s*]\s*>")

# An analysis of the MS-Word extensions is available at
# http://www.planetpublish.com/xmlarena/xap/Thursday/WordtoXML.pdf

_msmarkedsectionclose = re.compile(r"]\s*>")

# Regular expressions used for parsing


template_if_for_pattern = (
    r"(?:{%-?\s?(?:if|for)[^}]*?%}(?:.*?{%\s?end(?:if|for)[^}]*?-?%})+?)"
)

attribute_pattern: str = (
    rf"""
    (?:
        (
            (?:\w|-|\.|<)+ # (?:\w|-|\.)+ | required | checked   # [^>]
        )? # attribute name
        (?:  [ ]*?=[ ]*? # followed by "="
            (
                \"[^\"]*? # double quoted attribute
                (?:
                    {template_if_for_pattern} # if or for loop
                   | {{{{.*?}}}} # template stuff
                   | {{%[^}}]*?%}}
                   | [^\"] # anything else
                )*?
                \" # closing quote
              | '[^']*? # single quoted attribute
                (?:
                    {template_if_for_pattern} # if or for loop
                   | {{{{.*?}}}} # template stuff
                   | {{%[^}}]*?%}}
                   | [^'] # anything else
                )*?
                \' # closing quote
              | (?:\w|-)+ # or a non-quoted string value
              | {{{{.*?}}}} # a non-quoted template var
              | {{%[^}}]*?%}} # a non-quoted template tag
              | {template_if_for_pattern} # a non-quoted if statement
              | \/\*.*?\*\/ # messy comment

            )
        )? # attribute value
    )
    | ({template_if_for_pattern}
    """
    + r"""
    | {{.*?}}
    | {\#.*?\#}
    | {%.*?%})
"""
)

interesting_normal = re.compile(r"[&<{@\\]")
incomplete = re.compile("&[a-zA-Z#]")

entityref = re.compile("&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]")
charref = re.compile("&#(?:[0-9]+|[xX][0-9a-fA-F]+)[^0-9a-fA-F]")

starttagopen = re.compile("<[a-zA-Z]")
starttagopen_curly_perc = re.compile(r"{%")
commentopen_curly_perc = re.compile(r"{%\s*comment\s*(?:('|\")(.*?)\1)?\s*%}", re.I)
commentclose_curly_perc = re.compile(r"{%\s*endcomment", re.I)
endtag_curly_perc = re.compile(r"{%-?\s*end", re.I)
piclose = re.compile(">")
commentclose = re.compile(r"--\s*>")
# Note:
#  1) if you change tagfind/attrfind remember to update locatestarttagend too;
#  2) if you change tagfind/attrfind and/or locatestarttagend the parser will
#     explode, so don't do it.
# see http://www.w3.org/TR/html5/tokenization.html#tag-open-state
# and http://www.w3.org/TR/html5/tokenization.html#tag-name-state

tagfind_tolerant = re.compile(r"([a-zA-Z][^\t\n\r\f />\x00]*)(?:\s|/(?!>))*")
# print(r"([a-zA-Z][^\t\n\r\f />\x00]*)\s*((?:" + attribute_pattern + r")\s*)*\s*")
# tagfind_tolerant = re.compile(r"([a-zA-Z][^\t\n\r\f />\x00]*)\s*((?:" + attribute_pattern + r")\s*)*\s*", re.VERBOSE)


tagfind_tolerant_curly_perc_end = re.compile(
    r"-?\s*end([a-zA-Z](?:(?!-?%}|\t|\n|\r|\f| |\x00).)*)(?:\s|(?!-?%}))*"
)

attrfind_tolerant_curly_perc = re.compile(
    r'((?<=[\'"\s/])(?:(?!-?%}|\s|/).)(?:(?!-?%}|\s|/|=).)*)(\s*=+\s*(\'[^\']*\'|"[^"]*"|(?![\'"])(?:(?!-?%}|\s).)*))?(?:\s|(?!-?%}))*'
)
attrfind_tolerant_curly = re.compile(
    r'((?<=[\'"\s/])(?:(?!}}|\s|/).)(?:(?!}}|\s|/|=).)*)(\s*=+\s*(\'[^\']*\'|"[^"]*"|(?![\'"])(?:(?!}}|\s).)*))?(?:\s|(?!}}))*'
)

attrfind_tolerant = re.compile(
    r'((?<=[\'"\s/])[^\s/>][^\s/=>]*)(\s*=+\s*'
    r'(\'[^\']*\'|"[^"]*"|(?![\'"])[^>\s]*))?(?:\s|/(?!>))*'
)
# print(r"<[a-zA-Z][^\t\n\r\f />\x00]*\s*((?:" + attribute_pattern + r")\s*)*\s*")
# locatestarttagend_tolerant = re.compile(r"<[a-zA-Z][^\t\n\r\f />\x00]*\s*((?:" + attribute_pattern + r")\s*)*\s*", re.VERBOSE)
# print(r"<[a-zA-Z][^\t\n\r\f[ ]/>\x00]*\s*((?:" + attribute_pattern + r")\s*)*\s*")
# print(r"<[a-zA-Z][^\t\n\r\f />\x00]*\s*(" + attribute_pattern + r"|\s*)*\s*")
locatestarttagend_tolerant = re.compile(
    r"""
<([a-zA-Z][^\t\n\r\f />\x00]*)       # tag name
    (?:(?:\s|/(?!>))*                          # optional whitespace before attribute name
        (?:(?<=['"\s/])[^\s/>][^\s/=>]*  # attribute name
            (?:\s*=+\s*                    # value indicator
                (?: '[^']*'                   # LITA-enclosed value
                  | "[^"]*"                   # LIT-enclosed value
                  | (?!['"])[^>\s]*           # bare value
                  | {%(?:(?!%}).)*%}         # {% %}
                  | {{(?:(?!}}).)*}}         # {{ }}
                  | \\{{(?:(?!}}).)*}}       # \{{ }}
                  | {#(?:(?!#}).)*#}         # {# #}
                )
                \s*                          # possibly followed by a space
            )?
            (?: \s
              | /(?!>)
              | {%(?:(?!%}).)*%}         # {% %}
              | {{(?:(?!}}).)*}}         # {{ }}
              | \\{{(?:(?!}}).)*}}       # \{{ }}
              | {#(?:(?!#}).)*#}         # {# #}
              | [^/>]
            )*
        )*
   )?
\s*                                # trailing whitespace
""",
    re.VERBOSE,
)

find_curly_percent = re.compile(
    r"{%-?\+?\s*([a-zA-Z](?:(?!-?\+?%}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!-?\+?%}).)*)-?\+?%}"
)
find_curly_two = re.compile(
    r"{{~?\s*(.(?:(?!~?}}|\t|\n|\r|\f| |\x00|\|).)*)((?:\s|(?!~?}}).)*)~?}}"
)
find_curly_three = re.compile(r"{{{((?:(?!}}}).)*?)}}}")
find_curly_four = re.compile(
    r"{{{{~?\s*(.(?:(?!~?}}}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}}}).)*)~?}}}}"
)
find_curly_four_slash = re.compile(
    r"{{{{~?/\s*(.(?:(?!~?}}}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}}}).)*)~?}}}}"
)
find_curly_two_hash = re.compile(
    r"{{~?#\s*(.(?:(?!~?}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}).)*)~?}}"
)
find_slash_curly_two = re.compile(
    r"\\{{\s*(.(?:(?!}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!}}).)*)}}"
)
find_curly_two_exclaim = re.compile(r"{{\!(?:--)?((?:(?!}}).)*?)}}")

find_curly_two_slash = re.compile(
    r"{{~?\/\s*(.(?:(?!~?}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}).)*)~?}}"
)

locatestartend_tolerant_curly_hash = re.compile(
    r"""
  {{#[a-zA-Z](?:(?!}}|\t|\n|\r|\f| |\x00).)*       # tag name
  (?:[\s/]*                                             # optional whitespace before attribute name
    (?:'[^']*'                   # LITA-enclosed value
      |"[^"]*"                   # LIT-enclosed value
      |(?!['"])(?:(?!}}|\s).)*       # bare value
    )*
  )*
  \s*                                # trailing whitespace
""",
    re.VERBOSE,
)


locatestarttempend_tolerant = re.compile(
    r"""
  {{[\s/]*[a-zA-Z](?:(?!}}|\t|\n|\r|\f| |\x00).)*       # tag name
  (?:[\s/]*                                             # optional whitespace before attribute name
    (?:(?!\s}}.)*)                                       # attribute name
  )
  \s*                                # trailing whitespace
""",
    re.VERBOSE,
)


endendtag = re.compile(">")


# the HTML 5 spec, section 8.1.2.2, doesn't allow spaces between
# </ and the tag name, so maybe this should be fixed
endtagfind = re.compile(r"</\s*([a-zA-Z][-.a-zA-Z0-9:_]*)\s*>")
endtagfind_curly_perc = re.compile(
    r"{%-?\s*end([a-zA-Z][-.a-zA-Z0-9:_]*)(.*?)\s*-?%}", re.I
)


class Htp(_markupbase.ParserBase):
    """Find tags and other markup and call handler functions.

    Usage:
        p = Htp()
        p.feed(data)
        ...
        p.close()
    Start tags are handled by calling self.handle_starttag() or
    self.handle_startendtag(); end tags by self.handle_endtag().  The
    data between tags is passed from the parser to the derived class
    by calling self.handle_data() with the data as argument (the data
    may be split up in arbitrary chunks).  If convert_charrefs is
    True the character references are converted automatically to the
    corresponding Unicode character (and self.handle_data() is no
    longer split in chunks), otherwise they are passed by calling
    self.handle_entityref() or self.handle_charref() with the string
    containing respectively the named or numeric reference as the
    argument.
    """

    CDATA_CONTENT_ELEMENTS = ("script", "style")

    def __init__(self, *, convert_charrefs=True):
        """Initialize and reset this instance.

        If convert_charrefs is True (the default), all character references
        are automatically converted to the corresponding Unicode characters.
        """
        self.convert_charrefs = convert_charrefs
        self.reset()

    def reset(self):
        """Reset this instance.  Loses all unprocessed data."""
        self.lineno = 1
        self.offset = 0
        self.rawdata = ""
        self.lasttag = "???"
        self.interesting = interesting_normal
        self.cdata_elem = None
        _markupbase.ParserBase.reset(self)

    def getpos(self):
        """Return current line number and offset."""
        return self.lineno, self.offset

    # Internal -- update line number and offset.  This should be
    # called for each piece of data exactly once, in order -- in other
    # words the concatenation of all the input strings to this
    # function should be exactly the entire input.
    def updatepos(self, i, j):
        if i >= j:
            return j
        rawdata = self.rawdata
        nlines = rawdata.count("\n", i, j)
        if nlines:
            self.lineno = self.lineno + nlines
            pos = rawdata.rindex("\n", i, j)  # Should not fail
            self.offset = j - (pos + 1)
        else:
            self.offset = self.offset + j - i
        return j

    _decl_otherchars = ""

    def feed(self, data):
        r"""Feed data to the parser.

        Entire snippets should be fed as the
        parser is more forgiving for poor attributes than a normal html
        parser.

        # don't do this:
        # Call this as often as you want, with as little or as much text
        # as you want (may include '\n').
        """
        # self.rawdata = self.rawdata + data
        self.rawdata = data
        self.goahead(0)

    def close(self):
        """Handle any buffered data."""
        self.goahead(1)

    __starttag_text = None

    def get_starttag_text(self):
        """Return full source of start tag: '<...>'."""
        return self.__starttag_text

    def set_cdata_mode(self, elem):
        self.cdata_elem = elem.lower()
        self.interesting = re.compile(r"</\s*%s\s*>" % self.cdata_elem, re.I)

    def clear_cdata_mode(self):
        self.interesting = interesting_normal
        self.cdata_elem = None

    # Internal -- handle data as far as reasonable.  May leave state
    # and data to be processed by a subsequent call.  If 'end' is
    # true, force handling all data as if followed by EOF marker.
    def goahead(self, end):
        rawdata = self.rawdata
        # print(rawdata)
        i = 0
        n = len(rawdata)
        while i < n:
            if self.convert_charrefs and not self.cdata_elem:
                # j = rawdata.find('<', i)
                start_match = re.search(r"<|{|@|\\{{", rawdata[i:])
                j = start_match.start() + i if start_match else -1
                if j < 0:
                    # if we can't find the next <, either we are at the end
                    # or there's more text incoming.  If the latter is True,
                    # we can't pass the text to handle_data in case we have
                    # a charref cut in half at end.  Try to determine if
                    # this is the case before proceeding by looking for an
                    # & near the end and see if it's followed by a space or ;.
                    amppos = rawdata.rfind("&", max(i, n - 34))
                    if amppos >= 0 and not re.compile(r"[\s;]").search(rawdata, amppos):
                        break  # wait till we get all the text
                    j = n
            else:
                match = self.interesting.search(rawdata, i)  # < or &
                if match:
                    j = match.start()
                else:
                    if self.cdata_elem:
                        break
                    j = n
            if i < j:
                if self.convert_charrefs and not self.cdata_elem:
                    self.handle_data(unescape(rawdata[i:j]))
                else:
                    self.handle_data(rawdata[i:j])
            i = self.updatepos(i, j)

            if i == n:
                break
            startswith = rawdata.startswith
            if startswith("<", i):
                # print(i, rawdata[i:])
                if starttagopen.match(rawdata, i):  # < + letter
                    k = self.parse_starttag(i)
                elif startswith("</", i):
                    k = self.parse_endtag(i)
                elif startswith("<!--", i):
                    k = self.parse_comment(i)
                elif startswith("<?", i):
                    k = self.parse_pi(i)
                elif startswith("<!", i):
                    k = self.parse_html_declaration(i)
                elif (i + 1) < n:
                    self.handle_data("<")
                    k = i + 1
                else:
                    break

                if k < 0:
                    if not end:
                        break
                    k = rawdata.find(">", i + 1)
                    if k < 0:
                        k = rawdata.find("<", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1

                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])
                i = self.updatepos(i, k)
            elif startswith("&#", i):
                match = charref.match(rawdata, i)
                if match:
                    name = match.group()[2:-1]
                    self.handle_charref(name)
                    k = match.end()
                    if not startswith(";", k - 1):
                        k = k - 1
                    i = self.updatepos(i, k)
                    continue
                else:
                    if ";" in rawdata[i:]:  # bail by consuming &#
                        self.handle_data(rawdata[i : i + 2])
                        i = self.updatepos(i, i + 2)
                    break
            elif startswith("&", i):
                match = entityref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    self.handle_entityref(name)
                    k = match.end()
                    if not startswith(";", k - 1):
                        k = k - 1
                    i = self.updatepos(i, k)
                    continue
                match = incomplete.match(rawdata, i)
                if match:
                    # match.group() will contain at least 2 chars
                    if end and match.group() == rawdata[i:]:
                        k = match.end()
                        if k <= i:
                            k = n
                        i = self.updatepos(i, i + 1)
                    # incomplete
                    break
                elif (i + 1) < n:
                    # not the end of the buffer, and can't be confused
                    # with some other construct
                    self.handle_data("&")
                    i = self.updatepos(i, i + 1)
                else:
                    break
            elif startswith("{%", i):
                if endtag_curly_perc.match(rawdata, i):
                    k = self.parse_endtag_curly_perc(i)
                elif starttagopen_curly_perc.match(rawdata, i):
                    k = self.parse_starttag_curly_perc(i)

                if k < 0:
                    if not end:
                        break
                    k = rawdata.find("%}", i + 1)
                    if k < 0:
                        k = rawdata.find("{%", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)
            elif startswith("{#", i):
                k = self.parse_comment_curly_hash(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("#}", i + 1)
                    if k < 0:
                        k = rawdata.find("{#", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)
            elif startswith("{{!", i):
                # {{! }} or {{!-- }}
                # handlebarsjs comments
                k = self.parse_comment_curly_two_exlaim(i)
                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{!", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)
            elif startswith("@*", i):
                k = self.parse_comment_at_star(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("*@", i + 1)
                    if k < 0:
                        k = rawdata.find("@*", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            elif startswith("{{#", i) or startswith("{{~#", i):
                # {{# }}
                k = self.parse_starttag_curly_two_hash(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{#", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            elif startswith("{{/", i) or startswith("{{~/", i):
                # {{/ }}
                k = self.parse_endtag_curly_two_slash(i)
                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{/", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            elif startswith("{{{{/", i) or startswith("{{{{~/", i):
                # {{{{/ }}}} handlebars raw block
                k = self.parse_endtag_curly_four(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{{{/", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            elif startswith("{{{{", i):
                # {{{{ }}}} handlebars raw block
                k = self.parse_starttag_curly_four(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{{{", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            elif startswith(r"{{{", i):
                # handlebars un-escaped html
                # {{{ stuff ... }}}
                k = self.parse_curly_three(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            elif startswith("\\{{", i):
                # \{{ stuff ... }}
                # handlebars/mustache inline raw block
                k = self.parse_slash_curly_two(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)
            elif startswith("{{", i):
                # {{ stuff ... }}
                k = self.parse_curly_two(i)

                if k < 0:

                    if not end:
                        break
                    k = rawdata.find("}}", i + 1)
                    if k < 0:
                        k = rawdata.find("{{", i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            # need to handle any { statements here
            elif startswith("{", i):
                next_curly = re.search(r"<|{|@", rawdata[i + 1 :])
                k = next_curly.start() + i if next_curly else -1

                if k < 0:
                    k = i + 1
                else:
                    k += 1

                if self.convert_charrefs and not self.cdata_elem:
                    self.handle_data(unescape(rawdata[i:k]))
                else:
                    self.handle_data(rawdata[i:k])

                i = self.updatepos(i, k)

            else:
                assert 0, "interesting.search() lied"
        # end while
        if end and i < n and not self.cdata_elem:
            if self.convert_charrefs and not self.cdata_elem:
                self.handle_data(unescape(rawdata[i:n]))
            else:
                self.handle_data(rawdata[i:n])
            i = self.updatepos(i, n)
        self.rawdata = rawdata[i:]

    # Internal -- parse html declarations, return length or -1 if not terminated
    # See w3.org/TR/html5/tokenization.html#markup-declaration-open-state
    # See also parse_declaration in _markupbase
    def parse_html_declaration(self, i):
        rawdata = self.rawdata
        assert rawdata[i : i + 2] == "<!", (
            "unexpected call to " "parse_html_declaration()"
        )
        if rawdata[i : i + 4] == "<!--":
            # this case is actually already handled in goahead()
            return self.parse_comment(i)
        elif rawdata[i : i + 3] == "<![":
            return self.parse_marked_section(i)
        elif rawdata[i : i + 9].lower() == "<!doctype":
            # find the closing >
            gtpos = rawdata.find(">", i + 9)
            if gtpos == -1:
                return -1
            self.handle_decl(rawdata[i + 2 : gtpos])
            return gtpos + 1
        else:
            return self.parse_bogus_comment(i)

    # Internal -- parse bogus comment, return length or -1 if not terminated
    # see http://www.w3.org/TR/html5/tokenization.html#bogus-comment-state
    def parse_bogus_comment(self, i, report=1):
        rawdata = self.rawdata
        assert rawdata[i : i + 2] in ("<!", "</"), (
            "unexpected call to " "parse_comment()"
        )
        pos = rawdata.find(">", i + 2)
        if pos == -1:
            return -1
        if report:
            self.handle_comment(rawdata[i + 2 : pos])
        return pos + 1

    # Internal -- parse processing instr, return end or -1 if not terminated
    def parse_pi(self, i):
        rawdata = self.rawdata
        assert rawdata[i : i + 2] == "<?", "unexpected call to parse_pi()"
        match = piclose.search(rawdata, i + 2)  # >
        if not match:
            return -1
        j = match.start()
        self.handle_pi(rawdata[i + 2 : j])
        j = match.end()
        return j

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag(self, i):
        # print("start")
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        # print(endpos)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        # print(endpos, rawdata[i:endpos])
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        props = []

        # print(rawdata[i+1:])
        # match = tagfind_tolerant.match(rawdata, i + 1)
        match = locatestarttagend_tolerant.match(rawdata, i)
        # print("match", match)
        assert match, "unexpected call to parse_starttag()"
        k = match.end()

        self.lasttag = tag = match.group(1).lower()

        end = rawdata[k:endpos].strip()
        # print(end)

        # just grab all attributes to a string
        # where they can be processed after using the attribute-parser
        attrs = rawdata[i + 1 + len(tag) : endpos - len(end)].strip()
        # print(attrs)

        k = endpos - 1

        # print("K",k)

        # print(end)

        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            self.handle_data(rawdata[i:endpos])
            return endpos
        if end.endswith("/>"):
            # XHTML-style empty tag: <span attr="value" />
            props.append("is-selfclosing")
            self.handle_startendtag(tag, attrs, props)
        else:
            self.handle_starttag(tag, attrs, props)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag)
        return endpos

    def parse_starttag_curly_two_hash(self, i):
        self.__starttag_text = None
        rawdata = self.rawdata

        match = find_curly_two_hash.match(rawdata, i)
        if not match:
            return -1

        endpos = match.end()

        self.__starttag_text = rawdata[i:endpos]

        props = []

        if self.__starttag_text.startswith("{{~"):
            props.append("spaceless-left")

        if self.__starttag_text.endswith("~}}"):
            props.append("spaceless-right")

        attrs = match.group(2).strip()

        self.lasttag = tag = match.group(1).lower()

        self.handle_starttag_curly_two_hash(tag.strip(), attrs, props)

        return endpos

    def parse_starttag_curly_four(self, i):
        self.__starttag_text = None
        rawdata = self.rawdata

        match = find_curly_four.match(rawdata, i)

        if not match:
            return -1
        endpos = match.end()

        if endpos < 0:
            return endpos

        self.__starttag_text = rawdata[i:endpos]

        props = []

        if self.__starttag_text.startswith("{{{{~"):
            props.append("spaceless-left")

        if self.__starttag_text.endswith("~}}}}"):
            props.append("spaceless-right")

        attrs = match.group(2).strip()

        self.lasttag = tag = match.group(1).lower()

        self.handle_starttag_curly_four(tag.strip(), attrs, props)

        return endpos

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag_curly_perc(self, i):
        self.__starttag_text = None

        rawdata = self.rawdata
        match = find_curly_percent.match(rawdata, i)

        if not match:
            return -1

        endpos = match.end()

        props = []

        self.__starttag_text = rawdata[i:endpos]

        if self.__starttag_text.startswith("{%-"):
            props.append("spaceless-left")

        if self.__starttag_text.endswith("-%}"):
            props.append("spaceless-right")

        if self.__starttag_text.startswith("{%+"):
            props.append("disable-spaceless-left")

        if self.__starttag_text.endswith("+%}"):
            props.append("diable-spaceless-right")

        self.lasttag = tag = match.group(1).lower()
        attrs = match.group(2).strip()

        if tag.strip() == "comment":
            self.handle_starttag_comment_curly_perc(tag.strip(), attrs, props)
        else:
            self.handle_starttag_curly_perc(tag.strip(), attrs, props)
        if tag in self.CDATA_CONTENT_ELEMENTS:
            self.set_cdata_mode(tag)

        return endpos

    def parse_slash_curly_two(self, i):

        rawdata = self.rawdata
        match = find_slash_curly_two.match(rawdata, i)

        if not match:
            return -1

        endpos = match.end()

        attrs = match.group(2).strip()

        tag = match.group(1).lower()

        self.handle_slash_curly_two(tag.strip(), attrs)

        return endpos

    def parse_curly_two(self, i):

        rawdata = self.rawdata

        match = find_curly_two.match(rawdata, i)

        if not match:
            return -1

        endpos = match.end()

        attrs = match.group(2).strip()

        tag = match.group(1).lower()
        tag_text = match.group()
        props = []
        if tag_text.startswith("{{!--"):
            props.append("safe-left")

        if tag_text.endswith("--}}"):
            props.append("safe-right")

        if tag_text.startswith("{{~"):
            props.append("spaceless-left")

        if tag_text.endswith("~}}"):
            props.append("spaceless-right")

        self.handle_curly_two(tag.strip(), attrs, props)

        return endpos

    def parse_curly_three(self, i):
        rawdata = self.rawdata

        match = find_curly_three.match(rawdata, i)

        if not match:
            return -1

        endpos = match.end()

        data = match.group(1)

        self.handle_curly_three(data.strip())

        return endpos

    # Internal -- check to see if we have a complete starttag; return end
    # or -1 if incomplete.
    def check_for_whole_start_tag(self, i):
        rawdata = self.rawdata
        # print(rawdata[i:])
        m = locatestarttagend_tolerant.match(rawdata, i)
        # print(m)
        if m:
            j = m.end()
            next = rawdata[j : j + 1]
            if next == ">":
                return j + 1
            if next == "/":
                if rawdata.startswith("/>", j):
                    return j + 2
                if rawdata.startswith("/", j):
                    # buffer boundary
                    return -1
                # else bogus input
                if j > i:
                    return j
                else:
                    return i + 1
            if next == "-":
                if rawdata.startswith("-%}", j):
                    return j + 3
            if next == "%":
                if rawdata.startswith("%}", j):
                    return j + 2
                if rawdata.startswith("%", j):
                    # buffer boundary
                    return -1
            if next == "}":
                if rawdata.startswith("}}", j):
                    return j + 2
                if rawdata.startswith("}", j):
                    # buffer boundary
                    return -1
            if next == "":
                # end of input
                return -1
            if next in ("abcdefghijklmnopqrstuvwxyz=/" "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                # end of input in or before attribute value, or we have the
                # '/' from a '/>' ending
                return -1
            if j > i:
                return j
            else:
                return i + 1
        raise AssertionError("we should not get here!")

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag(self, i):
        rawdata = self.rawdata
        assert rawdata[i : i + 2] == "</", "unexpected call to parse_endtag"
        match = endendtag.search(rawdata, i + 1)  # >
        if not match:
            return -1
        gtpos = match.end()
        match = endtagfind.match(rawdata, i)  # </ + tag + >
        if not match:
            if self.cdata_elem is not None:
                self.handle_data(rawdata[i:gtpos])
                return gtpos
            # find the name: w3.org/TR/html5/tokenization.html#tag-name-state
            namematch = tagfind_tolerant.match(rawdata, i + 2)
            if not namematch:
                # w3.org/TR/html5/tokenization.html#end-tag-open-state
                if rawdata[i : i + 3] == "</>":
                    return i + 3
                else:
                    return self.parse_bogus_comment(i)
            tagname = namematch.group(1).lower()
            # consume and ignore other stuff between the name and the >
            # Note: this is not 100% correct, since we might have things like
            # </tag attr=">">, but looking for > after the name should cover
            # most of the cases and is much simpler
            gtpos = rawdata.find(">", namematch.end())
            self.handle_endtag(tagname)
            return gtpos + 1

        elem = match.group(1).lower()  # script or style
        if self.cdata_elem is not None:
            if elem != self.cdata_elem:
                self.handle_data(rawdata[i:gtpos])
                return gtpos

        self.handle_endtag(elem)
        self.clear_cdata_mode()
        return gtpos

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag_curly_perc(self, i):
        rawdata = self.rawdata
        props = []

        if rawdata[i:].startswith("{%-"):
            props.append("spaceless-left")

        assert rawdata[i : i + 2] == "{%", "unexpected call to parse_endtag"

        match = endtagfind_curly_perc.match(rawdata, i)

        if not match:
            return -1

        if rawdata[i:].endswith("-%}"):
            props.append("spaceless-right")

        attrs = match.group(2).strip()
        j = match.end()
        # match = endtagfind_curly_perc.match(rawdata, i)  # </ + tag + >

        tag = match.group(1).lower()  # script or style

        if tag == "comment":
            self.handle_endtag_comment_curly_perc(tag, props)
        else:
            self.handle_endtag_curly_perc(tag, attrs, props)
        self.clear_cdata_mode()
        return j

    def parse_endtag_curly_two_slash(self, i):

        self.__starttag_text = None

        rawdata = self.rawdata
        match = find_curly_two_slash.match(rawdata, i)

        if not match:
            return -1

        endpos = match.end()

        props = []

        tag_text = match.group()
        tag = match.group(1)

        if tag_text.startswith("{{~"):
            props.append("spaceless-left")

        if tag_text.endswith("~}}"):
            props.append("spaceless-right")

        self.handle_endtag_curly_two_slash(tag, props)

        return endpos

    def parse_endtag_curly_four(self, i):

        self.__starttag_text = None
        rawdata = self.rawdata

        match = find_curly_four_slash.match(rawdata, i)

        if not match:
            return -1
        endpos = match.end()

        if endpos < 0:
            return endpos

        tag_text = match.group()
        tag = match.group(1)
        props = []

        if tag_text.startswith("{{{{~"):
            props.append("spaceless-left")

        if tag_text.endswith("~}}}}"):
            props.append("spaceless-right")

        attrs = match.group(2).strip()

        self.handle_endtag_curly_four_slash(tag.strip(), attrs, props)

        return endpos

    # Internal -- parse declaration (for use by subclasses).
    def parse_declaration(self, i):
        # This is some sort of declaration; in "HTML as
        # deployed," this should only be the document type
        # declaration ("<!DOCTYPE html...>").
        # ISO 8879:1986, however, has more complex
        # declaration syntax for elements in <!...>, including:
        # --comment--
        # [marked section]
        # name in the following list: ENTITY, DOCTYPE, ELEMENT,
        # ATTLIST, NOTATION, SHORTREF, USEMAP,
        # LINKTYPE, LINK, IDLINK, USELINK, SYSTEM
        rawdata = self.rawdata
        j = i + 2
        assert rawdata[i:j] == "<!", "unexpected call to parse_declaration"
        if rawdata[j : j + 1] == ">":
            # the empty comment <!>
            return j + 1
        if rawdata[j : j + 1] in ("-", ""):
            # Start of comment followed by buffer boundary,
            # or just a buffer boundary.
            return -1
        # A simple, practical version could look like: ((name|stringlit) S*) + '>'
        n = len(rawdata)
        if rawdata[j : j + 2] == "--":  # comment
            # Locate --.*-- as the body of the comment
            return self.parse_comment(i)
        elif rawdata[j] == "[":  # marked section
            # Locate [statusWord [...arbitrary SGML...]] as the body of the marked section
            # Where statusWord is one of TEMP, CDATA, IGNORE, INCLUDE, RCDATA
            # Note that this is extended by Microsoft Office "Save as Web" function
            # to include [if...] and [endif].
            return self.parse_marked_section(i)
        else:  # all other declaration elements
            decltype, j = self._scan_name(j, i)
        if j < 0:
            return j
        if decltype == "doctype":
            self._decl_otherchars = ""
        while j < n:
            c = rawdata[j]
            if c == ">":
                # end of declaration syntax
                data = rawdata[i + 2 : j]
                if decltype == "doctype":
                    self.handle_decl(data)
                else:
                    # According to the HTML5 specs sections "8.2.4.44 Bogus
                    # comment state" and "8.2.4.45 Markup declaration open
                    # state", a comment token should be emitted.
                    # Calling unknown_decl provides more flexibility though.
                    self.unknown_decl(data)
                return j + 1
            if c in "\"'":
                m = _declstringlit_match(rawdata, j)
                if not m:
                    return -1  # incomplete
                j = m.end()
            elif c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
                name, j = self._scan_name(j, i)
            elif c in self._decl_otherchars:
                j = j + 1
            elif c == "[":
                # this could be handled in a separate doctype parser
                if decltype == "doctype":
                    j = self._parse_doctype_subset(j + 1, i)
                elif decltype in {"attlist", "linktype", "link", "element"}:
                    # must tolerate []'d groups in a content model in an element declaration
                    # also in data attribute specifications of attlist declaration
                    # also link type declaration subsets in linktype declarations
                    # also link attribute specification lists in link declarations
                    raise AssertionError(
                        "unsupported '[' char in %s declaration" % decltype
                    )
                else:
                    raise AssertionError("unexpected '[' char in declaration")
            else:
                raise AssertionError("unexpected %r char in declaration" % rawdata[j])
            if j < 0:
                return j
        return -1  # incomplete

    # Internal -- parse a marked section
    # Override this to handle MS-word extension syntax <![if word]>content<![endif]>
    def parse_marked_section(self, i, report=1):
        rawdata = self.rawdata
        assert rawdata[i : i + 3] == "<![", "unexpected call to parse_marked_section()"
        sectName, j = self._scan_name(i + 3, i)
        if j < 0:
            return j
        if sectName in {"temp", "cdata", "ignore", "include", "rcdata"}:
            # look for standard ]]> ending
            match = _markedsectionclose.search(rawdata, i + 3)
        elif sectName in {"if", "else", "endif"}:
            # look for MS Office ]> ending
            match = _msmarkedsectionclose.search(rawdata, i + 3)
        else:
            raise AssertionError(
                "unknown status keyword %r in marked section" % rawdata[i + 3 : j]
            )
        if not match:
            return -1
        if report:
            j = match.start(0)
            self.unknown_decl(rawdata[i + 3 : j])
        return match.end(0)

    # Internal -- parse comment <!-- -->, return length or -1 if not terminated
    def parse_comment(self, i, report=1):
        rawdata = self.rawdata
        if rawdata[i : i + 4] != "<!--":
            raise AssertionError("unexpected call to parse_comment()")
        match = _commentclose.search(rawdata, i + 4)
        if not match:
            return -1
        if report:
            j = match.start(0)
            self.handle_comment(rawdata[i + 4 : j])
        return match.end(0)

    # Internal -- parse comment {# #}, return length or -1 if not terminated
    def parse_comment_curly_hash(self, i, report=1):
        rawdata = self.rawdata
        if rawdata[i : i + 2] != "{#":
            raise AssertionError("unexpected call to parse_comment_curly_hash()")
        match = _commentclosecurlyhash.search(rawdata, i + 2)
        if not match:
            return -1
        if report:
            j = match.start(0)
            self.handle_comment_curly_hash(rawdata[i + 2 : j])
        return match.end(0)

    # Internal -- parse comment {{! }} or {{!-- }}, return length or -1 if not terminated
    def parse_comment_curly_two_exlaim(self, i):
        # print("here!")
        rawdata = self.rawdata
        if rawdata[i : i + 3] != "{{!":
            raise AssertionError("unexpected call to parse_comment_curly_two_exlaim()")
        match = find_curly_two_exclaim.search(rawdata, i)
        # print(match)
        if not match:
            return -1

        tag_text = match.group()
        props = []
        if tag_text.startswith("{{!--"):
            props.append("safe-left")

        if tag_text.endswith("--}}"):
            props.append("safe-right")

        if tag_text.startswith("{{~"):
            props.append("spaceless-left")

        if tag_text.endswith("~}}"):
            props.append("spaceless-right")

        j = match.end()

        self.handle_comment_curly_two_exlaim(match.group(1), props)
        return j

    # Internal -- parse comment @* *@ , return length or -1 if not terminated
    def parse_comment_at_star(self, i, report=1):
        rawdata = self.rawdata
        if rawdata[i : i + 2] != "@*":
            raise AssertionError("unexpected call to parse_comment_at_star()")
        match = _commentcloseatstar.search(rawdata, i + 2)
        if not match:
            return -1
        if report:
            j = match.start(0)
            self.handle_comment_at_star(rawdata[i + 2 : j])
        return match.end(0)

    # Internal -- scan past the internal subset in a <!DOCTYPE declaration,
    # returning the index just past any whitespace following the trailing ']'.
    def _parse_doctype_subset(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        j = i
        while j < n:
            c = rawdata[j]
            if c == "<":
                s = rawdata[j : j + 2]
                if s == "<":
                    # end of buffer; incomplete
                    return -1
                if s != "<!":
                    self.updatepos(declstartpos, j + 1)
                    raise AssertionError(
                        "unexpected char in internal subset (in %r)" % s
                    )
                if (j + 2) == n:
                    # end of buffer; incomplete
                    return -1
                if (j + 4) > n:
                    # end of buffer; incomplete
                    return -1
                if rawdata[j : j + 4] == "<!--":
                    j = self.parse_comment(j, report=0)
                    if j < 0:
                        return j
                    continue
                name, j = self._scan_name(j + 2, declstartpos)
                if j == -1:
                    return -1
                if name not in {"attlist", "element", "entity", "notation"}:
                    self.updatepos(declstartpos, j + 2)
                    raise AssertionError(
                        "unknown declaration %r in internal subset" % name
                    )
                # handle the individual names
                meth = getattr(self, "_parse_doctype_" + name)
                j = meth(j, declstartpos)
                if j < 0:
                    return j
            elif c == "%":
                # parameter entity reference
                if (j + 1) == n:
                    # end of buffer; incomplete
                    return -1
                s, j = self._scan_name(j + 1, declstartpos)
                if j < 0:
                    return j
                if rawdata[j] == ";":
                    j = j + 1
            elif c == "]":
                j = j + 1
                while j < n and rawdata[j].isspace():
                    j = j + 1
                if j < n:
                    if rawdata[j] == ">":
                        return j
                    self.updatepos(declstartpos, j)
                    raise AssertionError("unexpected char after internal subset")
                else:
                    return -1
            elif c.isspace():
                j = j + 1
            else:
                self.updatepos(declstartpos, j)
                raise AssertionError("unexpected char %r in internal subset" % c)
        # end of buffer reached
        return -1

    # Internal -- scan past <!ELEMENT declarations
    def _parse_doctype_element(self, i, declstartpos):
        name, j = self._scan_name(i, declstartpos)
        if j == -1:
            return -1
        # style content model; just skip until '>'
        rawdata = self.rawdata
        if ">" in rawdata[j:]:
            return rawdata.find(">", j) + 1
        return -1

    # Internal -- scan past <!ATTLIST declarations
    def _parse_doctype_attlist(self, i, declstartpos):
        rawdata = self.rawdata
        name, j = self._scan_name(i, declstartpos)
        c = rawdata[j : j + 1]
        if c == "":
            return -1
        if c == ">":
            return j + 1
        while 1:
            # scan a series of attribute descriptions; simplified:
            #   name type [value] [#constraint]
            name, j = self._scan_name(j, declstartpos)
            if j < 0:
                return j
            c = rawdata[j : j + 1]
            if c == "":
                return -1
            if c == "(":
                # an enumerated type; look for ')'
                if ")" in rawdata[j:]:
                    j = rawdata.find(")", j) + 1
                else:
                    return -1
                while rawdata[j : j + 1].isspace():
                    j = j + 1
                if not rawdata[j:]:
                    # end of buffer, incomplete
                    return -1
            else:
                name, j = self._scan_name(j, declstartpos)
            c = rawdata[j : j + 1]
            if not c:
                return -1
            if c in "'\"":
                m = _declstringlit_match(rawdata, j)
                if m:
                    j = m.end()
                else:
                    return -1
                c = rawdata[j : j + 1]
                if not c:
                    return -1
            if c == "#":
                if rawdata[j:] == "#":
                    # end of buffer
                    return -1
                name, j = self._scan_name(j + 1, declstartpos)
                if j < 0:
                    return j
                c = rawdata[j : j + 1]
                if not c:
                    return -1
            if c == ">":
                # all done
                return j + 1

    # Internal -- scan past <!NOTATION declarations
    def _parse_doctype_notation(self, i, declstartpos):
        name, j = self._scan_name(i, declstartpos)
        if j < 0:
            return j
        rawdata = self.rawdata
        while 1:
            c = rawdata[j : j + 1]
            if not c:
                # end of buffer; incomplete
                return -1
            if c == ">":
                return j + 1
            if c in "'\"":
                m = _declstringlit_match(rawdata, j)
                if not m:
                    return -1
                j = m.end()
            else:
                name, j = self._scan_name(j, declstartpos)
                if j < 0:
                    return j

    # Internal -- scan past <!ENTITY declarations
    def _parse_doctype_entity(self, i, declstartpos):
        rawdata = self.rawdata
        if rawdata[i : i + 1] == "%":
            j = i + 1
            while 1:
                c = rawdata[j : j + 1]
                if not c:
                    return -1
                if c.isspace():
                    j = j + 1
                else:
                    break
        else:
            j = i
        name, j = self._scan_name(j, declstartpos)
        if j < 0:
            return j
        while 1:
            c = self.rawdata[j : j + 1]
            if not c:
                return -1
            if c in "'\"":
                m = _declstringlit_match(rawdata, j)
                if m:
                    j = m.end()
                else:
                    return -1  # incomplete
            elif c == ">":
                return j + 1
            else:
                name, j = self._scan_name(j, declstartpos)
                if j < 0:
                    return j

    # Internal -- scan a name token and the new position and the token, or
    # return -1 if we've reached the end of the buffer.
    def _scan_name(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        if i == n:
            return None, -1
        m = _declname_match(rawdata, i)
        if m:
            s = m.group()
            name = s.strip()
            if (i + len(s)) == n:
                return None, -1  # end of buffer
            return name.lower(), m.end()
        else:
            self.updatepos(declstartpos, i)
            raise AssertionError(
                "expected name token at %r" % rawdata[declstartpos : declstartpos + 20]
            )

    def unknown_decl(self, data):
        # handlers for unknown objects
        pass

    def handle_startendtag(self, tag, attrs, props):
        # start and end of tag <p/>
        self.handle_starttag(tag, attrs, props)
        self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs, props):
        # start tag <p>
        pass

    def handle_endtag(self, tag):
        # end tag </p>
        pass

    def handle_starttag_curly_perc(self, tag, attrs, props):
        # template start tag {% name %}
        pass

    def handle_endtag_curly_perc(self, tag, attrs, props):
        # template end tag {% endname %}
        pass

    def handle_starttag_curly_two_hash(self, tag, attrs, props):
        # handlebars/mustache loop {{#name attributes}}{{/name}}
        pass

    def handle_endtag_curly_two_slash(self, tag, props):
        # handlebars/mustache loop {{#name attributes}}{{/name}}
        pass

    def handle_starttag_curly_four(self, tag, attrs, props):
        # handlebars raw close {{{{raw}}}}{{{{/raw}}}}
        pass

    def handle_endtag_curly_four_slash(self, tag, attrs, props):
        # handlebars raw close {{{{raw}}}}{{{{/raw}}}}
        pass

    def handle_charref(self, name):
        # handle character reference
        pass

    def handle_entityref(self, name):
        # handle entity reference
        pass

    def handle_data(self, data):
        # handle data
        pass

    def handle_curly_two(self, data, attrs, props):
        # template value {{ value attrs }}
        pass

    def handle_slash_curly_two(self, data, attrs):
        # handlebars/mustache inline raw block
        pass

    def handle_curly_three(self, data):
        # handlebars un-escaped html
        pass

    def handle_comment(self, data):
        # comment <!-- -->
        pass

    def handle_comment_curly_hash(self, data):
        # django/jinja comment
        pass

    def handle_starttag_comment_curly_perc(self, data, attrs, props):
        # django multi line comment {% comment %}{% endcomment %}
        pass

    def handle_endtag_comment_curly_perc(self, data, props):
        # django multi line comment {% comment %}{% endcomment %}
        pass

    def handle_comment_curly_two_exlaim(self, data, props):
        # handlebars comment
        pass

    def handle_comment_at_star(self, data):
        # c# razor pages comment
        pass

    def handle_decl(self, decl):
        # handle declaration
        pass

    def handle_pi(self, data):
        # handle processing instruction
        pass
