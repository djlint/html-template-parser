"""Html Tag Attribute Parser.

Attributes are passed in as a complete string.

AttributeParser(attributes).parse()
"""
# pylint: disable=R0916
import re

curly_two = re.compile(
    r"{{~?\>?\s*(.(?:(?!~?}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}).)*)~?}}"
)
curly_three = re.compile(r"{{{((?:(?!}}).)*?)}}}")
curly_four = re.compile(
    r"{{{{~?\s*(.(?:(?!~?}}}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}}}).)*)~?}}}}"
)
curly_four_slash = re.compile(
    r"{{{{~?/\s*(.(?:(?!~?}}}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}}}).)*)~?}}}}"
)
curly_hash = re.compile(r"{#((?:(?!#}).)*?)#}")
at_star = re.compile(r"@\*((?:(?!\*@).)*?)\*@")
curly_two_exclaim = re.compile(r"{{\!(?:--)?\s*((?:(?!}}).)*?)(?:--)?}}")
curly_percent = re.compile(
    r"{%-?\+?\s*(end)?(.(?:(?!-?\+?%}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!-?\+?%}).)*)-?\+?%}"
)
curly_two_hash = re.compile(
    r"{{~?#\>?\s*(.(?:(?!~?}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}).)*)~?}}"
)
curly_two_slash = re.compile(
    r"{{~?\/\s*(.(?:(?!~?}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!~?}}).)*)~?}}"
)
slash_curly_two = re.compile(
    r"\\{{\s*(.(?:(?!}}|\t|\n|\r|\f| |\x00).)*)((?:\s|(?!}}).)*)}}"
)
space = re.compile(r"\s+")
space_equals = re.compile(r"\s*=")


class AttributeParser:
    """Parse attribute data.

    Usage:

    p = AttributeParser()
    p.feed(data)
    p.close()
    """

    def __init__(self):
        """Set up class stuff."""
        self.reset()

    def reset(self):
        self.lineno = 1
        self.offset = 0
        self.rawdata = ""

    def feed(self, data):
        """Send attributes to the parser."""
        self.rawdata = data
        self.parse()

    def updatepos(self, i, j):
        if i >= j:
            return j  # pragma: no cover
        rawdata = self.rawdata
        nlines = rawdata.count("\n", i, j)
        if nlines:
            self.lineno = self.lineno + nlines
            pos = rawdata.rindex("\n", i, j)  # Should not fail
            self.offset = j - (pos + 1)
        else:
            self.offset = self.offset + j - i
        return j

    def getpos(self):
        """Return current line number and offset."""
        return self.lineno, self.offset

    def get_element_text(self):
        return self.__element_text

    def parse(self):
        rawdata = self.rawdata
        i = 0
        n = len(rawdata)

        while i < n:
            position = i
            startswith = rawdata.startswith

            if startswith("{%", i):
                # template block
                k = self.parse_curly_perc(i)

                if k == -1:
                    k = self.parse_html(i)

                i = self.updatepos(i, k)

            elif startswith("{#", i):
                # django/jinja comment
                k = self.parse_curly_hash(i)

                if k == -1:
                    k = self.parse_html(i)

                i = self.updatepos(i, k)

            elif startswith("{{!", i):
                # handlebars comment
                k = self.parse_curly_two_exclaim(i)

                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("@*", i):
                # c# razor pages comments

                k = self.parse_at_star(i)
                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("{{#", i) or startswith("{{~#", i):
                # handlebars/mustache loop {{#name attributes}}{{/name}}
                k = self.parse_curly_two_hash(i)
                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("{{/", i) or startswith("{{~/", i):
                # handlebars/mustache endloop {{#name attributes}}{{/name}}
                k = self.parse_curly_two_slash(i)
                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("{{{{/", i) or startswith("{{{{~/", i):
                # handlebars raw close {{{{raw}}}}{{{{/raw}}}}
                k = self.parse_curly_four_slash(i)
                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("{{{{", i):
                # handlebars raw open {{{{raw}}}}{{{{/raw}}}}
                k = self.parse_curly_four(i)
                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith(r"{{{", i):
                # handlebars un-escaped html
                k = self.parse_curly_three(i)
                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("\\{{", i):
                # handlebars/mustache inline raw block
                k = self.parse_slash_curly_two(i)
                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("{{", i) or startswith("{{~"):
                # template variable. All have spaces around except handlebars/mustache
                k = self.parse_curly_two(i)

                if k == -1:
                    k = self.parse_html(i)
                i = self.updatepos(i, k)

            elif startswith("'", i) or startswith('"', i):
                # value start/end
                k = self.parse_value_start(i)
                i = self.updatepos(i, k)

            elif space.match(rawdata[i]):
                k = self.parse_space(i)
                i = self.updatepos(i, k)

            else:
                # parse normal html stuff
                k = self.parse_html(i)
                i = self.updatepos(i, k)

            if position == i:  # pragma: no cover
                assert 0, "should not get here."  # pragma: no cover

    def parse_curly_perc(self, i):
        self.__element_text = None
        rawdata = self.rawdata
        props = []

        match = curly_percent.match(rawdata, i)

        if not match:
            return -1

        self.__element_text = match.group()
        tag = match.group(2)
        attributes = match.group(3).strip() if match.group(3) else None

        if self.__element_text.startswith("{%-"):
            props.append("spaceless-left-dash")

        if self.__element_text.endswith("-%}"):
            props.append("spaceless-right-dash")

        if self.__element_text.startswith("{%+"):
            props.append("spaceless-left-plus")

        if self.__element_text.endswith("+%}"):
            props.append("spaceless-right-plus")

        j = match.end()

        if match.group(1) == "end":
            if tag == "comment":
                self.handle_endtag_comment_curly_perc(tag, attributes, props)
            else:
                self.handle_endtag_curly_perc(tag, attributes, props)
        else:
            if tag == "comment":
                self.handle_starttag_comment_curly_perc(tag, attributes, props)
            else:
                self.handle_starttag_curly_perc(tag, attributes, props)

        return j

    def parse_curly_hash(self, i):
        # django/jinja commment
        self.__element_text = None
        rawdata = self.rawdata

        match = curly_hash.match(rawdata, i)
        if not match:
            return -1
        self.__element_text = match.group()
        self.handle_comment_curly_hash(match.group(1).strip())

        j = match.end()
        return j

    def parse_curly_two_exclaim(self, i):
        # handlebars comment
        self.__element_text = None
        rawdata = self.rawdata
        props = []
        match = curly_two_exclaim.match(rawdata, i)

        if not match:
            return -1

        self.__element_text = match.group()

        if self.__element_text.startswith("{{!--"):
            props.append("safe-left")

        if self.__element_text.endswith("--}}"):
            props.append("safe-right")

        j = match.end()

        self.handle_comment_curly_two_exclaim(match.group(1), props)
        return j

    def parse_at_star(self, i):
        self.__element_text = None
        rawdata = self.rawdata

        match = at_star.match(rawdata, i)
        if not match:
            return -1

        j = match.end()
        self.__element_text = rawdata[i:j]
        self.handle_comment_at_star(match.group(1).strip())

        return j

    def parse_curly_two_hash(self, i):
        # handlebars/mustache loop {{#name attributes}}{{/name}}
        self.__element_text = None
        rawdata = self.rawdata
        props = []
        match = curly_two_hash.match(rawdata, i)

        if not match:
            return -1

        self.__element_text = match.group()
        tag = match.group(1)
        attributes = match.group(2).strip() if match.group(2) else None

        if self.__element_text.startswith("{{~"):
            props.append("spaceless-left-tilde")

        if self.__element_text.startswith("{{#>"):
            props.append("partial")

        if self.__element_text.endswith("~}}"):
            props.append("spaceless-right-tilde")

        j = match.end()

        self.handle_starttag_curly_two_hash(tag, attributes, props)

        return j

    def parse_curly_two_slash(self, i):
        # handlebars/mustache endloop {{#name attributes}}{{/name}}
        self.__element_text = None
        rawdata = self.rawdata
        props = []
        match = curly_two_slash.match(rawdata, i)

        if not match:
            return -1

        self.__element_text = match.group()
        tag = match.group(1)

        if self.__element_text.startswith("{{~"):
            props.append("spaceless-left-tilde")

        if self.__element_text.endswith("~}}"):
            props.append("spaceless-right-tilde")

        j = match.end()

        self.handle_endtag_curly_two_slash(tag, props)

        return j

    def parse_slash_curly_two(self, i):
        rawdata = self.rawdata
        self.__element_text = None
        match = slash_curly_two.match(rawdata, i)

        if not match:
            return -1

        tag = match.group(1)
        attributes = match.group(2).strip()
        self.__element_text = match.group()
        j = match.end()

        self.handle_slash_curly_two(tag, attributes)
        return j

    def parse_curly_four_slash(self, i):
        # handlebars raw close {{{{raw}}}}{{{{/raw}}}}
        rawdata = self.rawdata
        self.__element_text = None
        props = []
        match = curly_four_slash.match(rawdata, i)
        if not match:
            return -1

        self.__element_text = match.group()
        tag = match.group(1)

        j = match.end()

        if self.__element_text.startswith("{{{{~"):
            props.append("spaceless-left-tilde")

        if self.__element_text.endswith("~}}}}"):
            props.append("spaceless-right-tilde")

        attrs = match.group(2).strip()

        self.handle_endtag_curly_four_slash(tag, attrs, props)
        return j

    def parse_curly_three(self, i):
        # handlebars un-escaped html
        rawdata = self.rawdata
        self.__element_text = None

        match = curly_three.match(rawdata, i)
        if not match:
            return -1

        j = match.end()
        self.__element_text = match.group()

        self.handle_curly_three(match.group(1).strip())

        return j

    def parse_curly_four(self, i):
        # handlebars raw open {{{{raw}}}}{{{{/raw}}}}
        rawdata = self.rawdata
        self.__element_text = None
        props = []
        match = curly_four.match(rawdata, i)

        if not match:
            return -1

        self.__element_text = match.group()
        tag = match.group(1)

        if self.__element_text.startswith("{{{{~"):
            props.append("spaceless-left-tilde")

        if self.__element_text.endswith("~}}}}"):
            props.append("spaceless-right-tilde")

        j = match.end()

        attrs = match.group(2).strip()
        self.handle_starttag_curly_four(tag, attrs, props)
        return j

    def parse_curly_two(self, i):
        rawdata = self.rawdata
        self.__element_text = None
        props = []
        match = curly_two.match(rawdata, i)
        if not match:
            return -1

        self.__element_text = match.group()
        tag = match.group(1).strip()
        attributes = match.group(2).strip()
        if self.__element_text.startswith("{{~"):
            props.append("spaceless-left-tilde")

        if self.__element_text.startswith("{{>"):
            props.append("partial")

        if self.__element_text.endswith("~}}"):
            props.append("spaceless-right-tilde")

        j = match.end()

        self.handle_curly_two(tag, attributes, props)

        return j

    def parse_html(self, i):
        rawdata = self.rawdata
        self.__element_text = None
        props = []
        n = len(rawdata)
        j = i
        while j < n:
            c = rawdata[j]

            if c in ["{", "\\"]:
                startswith = rawdata.startswith

                if (
                    startswith("{%", j)
                    and curly_percent.match(rawdata, j)
                    or startswith("{#", j)
                    and curly_hash.match(rawdata, j)
                    or startswith("{{", j)
                    and curly_two.match(rawdata, j)
                    or startswith("@*", j)
                    and at_star.match(rawdata, j)
                    or startswith("\\{{", j)
                    and slash_curly_two.match(rawdata, j)
                ):
                    break

            if space_equals.match(rawdata[j:]):
                props.append("has-value")
                break
            elif space.match(c) or c in ['"', "'"]:
                break

            j += 1

        if rawdata[i:j].strip() != "":
            self.__element_text = rawdata[i:j]
            self.handle_name(rawdata[i:j], props)
            return j
        return j + 1

    def parse_value_start(self, i):
        rawdata = self.rawdata
        self.__element_text = rawdata[i]
        self.handle_value_start()
        return i + 1

    def parse_space(self, i):
        self.__element_text = None
        rawdata = self.rawdata

        match = space.match(rawdata, i)
        if not match:
            return i
        self.__element_text = match.group()
        j = match.end()

        self.handle_space(rawdata[i:j])

        return j

    # place holders
    def handle_starttag_curly_perc(self, tag, attrs, props):
        pass

    def handle_endtag_curly_perc(self, tag, attrs, props):
        pass

    def handle_starttag_comment_curly_perc(self, tag, attrs, props):
        # django multi line comment {% comment %}{% endcomment %}
        pass

    def handle_endtag_comment_curly_perc(self, tag, attrs, props):
        # django multi line comment {% comment %}{% endcomment %}
        pass

    def handle_comment_curly_hash(self, value):
        # django/jinja comment
        pass

    def handle_comment_curly_two_exclaim(self, value, props):
        # handlebars comment
        pass

    def handle_comment_at_star(self, value):
        # c# razor pages comment
        pass

    def handle_starttag_curly_two_hash(self, tag, attrs, props):
        # handlebars/mustache loop {{#name attributes}}{{/name}}
        pass

    def handle_endtag_curly_two_slash(self, tag, props):
        # handlebars/mustache loop {{#name attributes}}{{/name}}
        pass

    def handle_slash_curly_two(self, tag, attrs):
        # handlebars/mustache inline raw block
        pass

    def handle_endtag_curly_four_slash(self, tag, attrs, props):
        # handlebars raw close {{{{raw}}}}{{{{/raw}}}}
        pass

    def handle_starttag_curly_four(self, tag, attrs, props):
        # handlebars raw close {{{{raw}}}}{{{{/raw}}}}
        pass

    def handle_curly_three(self, value):
        # handlebars un-escaped html
        pass

    def handle_curly_two(self, tag, attrs, props):
        pass

    def handle_name(self, name, props):
        pass

    def handle_value_start(self):
        pass

    def handle_space(self, value):
        pass
