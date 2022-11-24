"""Tests for Htp.

Many tests are from python's HTMLParse library, expanded to include
html template parsing.

See Python's license: https://github.com/python/cpython/blob/main/LICENSE

https://github.com/python/cpython/blob/f4c03484da59049eb62a9bf7777b963e2267d187/Lib/test/test_htmlparser.py

"""
# pylint: disable=C0115,W0237,E1101,W0108,W1404,C3001

import pprint
import unittest

from HtmlTemplateParser import Htp


class EventCollector(Htp):
    def __init__(self, *args, **kw):
        self.events = []
        self.append = self.events.append
        Htp.__init__(self, *args, **kw)

    def get_events(self):
        # Normalize the list of events so that buffer artefacts don't
        # separate runs of contiguous characters.
        L = []
        prevtype = None
        for event in self.events:
            type = event[0]
            if type == prevtype == "data":
                L[-1] = ("data", L[-1][1] + event[1])
            else:
                L.append(event)
            prevtype = type
        self.events = L
        return L

    # structure markup

    def handle_starttag(self, tag, attrs, props):
        self.append(("starttag", tag, attrs, props))

    def handle_starttag_curly_perc(self, tag, attrs, props):
        self.append(("starttag_curly_perc", tag, attrs, props))

    def handle_starttag_curly_two_hash(self, tag, attrs, props):
        self.append(("starttag_curly_two_hash", tag, attrs, props))

    def handle_starttag_curly_four(self, tag, attrs, props):
        self.append(("starttag_curly_four", tag, attrs, props))

    def handle_startendtag(self, tag, attrs, props):
        self.append(("startendtag", tag, attrs, props))

    def handle_endtag(self, tag):
        self.append(("endtag", tag))

    def handle_endtag_curly_perc(self, tag, attrs, props):
        self.append(("endtag_curly_perc", tag, attrs, props))

    def handle_endtag_curly_hash(self, tag):
        self.append(("endtag_curly_hash", tag))

    def handle_endtag_curly_four_slash(self, tag, attrs, props):
        self.append(("endtag_curly_four", tag, attrs, props))

    def handle_curly_two(self, data, attrs, props):
        self.append(("curly_two", data, attrs, props))

    def handle_slash_curly_two(self, data, attrs):
        self.append(("slash_curly_two", data, attrs))

    def handle_curly_three(self, data):
        self.append(("curly_three", data))

    def handle_endtag_curly_two_slash(self, tag, props):
        self.append(("curly_two_slash", tag, props))

    # all other markup

    def handle_comment(self, data):
        self.append(("comment", data))

    def handle_comment_curly_hash(self, data):
        self.append(("comment_curly_hash", data))

    def handle_comment_curly_two_exlaim(self, data, props):
        self.append(("comment_curly_exlaim", data, props))

    def handle_comment_at_star(self, data):
        self.append(("comment_at_star", data))

    def handle_starttag_comment_curly_perc(self, data, attrs, props):
        self.append(("comment_curly_perc", data, attrs, props))

    def handle_endtag_comment_curly_perc(self, data, props):
        self.append(("comment_curly_perc_close", data, props))

    def handle_charref(self, data):
        self.append(("charref", data))

    def handle_data(self, data):
        self.append(("data", data))

    def handle_decl(self, data):
        self.append(("decl", data))

    def handle_entityref(self, data):
        self.append(("entityref", data))

    def handle_pi(self, data):
        self.append(("pi", data))

    def unknown_decl(self, decl):
        self.append(("unknown decl", decl))


class EventCollectorExtra(EventCollector):
    def handle_starttag(self, tag, attrs, props):
        EventCollector.handle_starttag(self, tag, attrs, props)
        self.append(("starttag_text", self.get_element_text()))


class EventCollectorCharrefs(EventCollector):
    def handle_charref(self, data):
        self.fail("This should never be called with convert_charrefs=True")

    def handle_entityref(self, data):
        self.fail("This should never be called with convert_charrefs=True")


class TestCaseBase(unittest.TestCase):
    def get_collector(self):
        return EventCollector(convert_charrefs=False)

    def _run_check(self, source, expected_events, collector=None):
        if collector is None:
            collector = self.get_collector()
        parser = collector

        if isinstance(source, list):

            for s in source:
                parser.feed(s)

        else:
            parser.feed(source)
        parser.close()
        events = parser.get_events()
        if events != expected_events:
            self.fail(
                "received events did not match expected events"
                + "\nSource:\n"
                + repr(source)
                + "\nExpected:\n"
                + pprint.pformat(expected_events)
                + "\nReceived:\n"
                + pprint.pformat(events)
            )

    def _run_check_extra(self, source, events):
        self._run_check(source, events, EventCollectorExtra(convert_charrefs=False))


class HtpTestCase(TestCaseBase):
    def test_processing_instruction_only(self):
        self._run_check(
            "<?processing instruction>",
            [
                ("pi", "processing instruction"),
            ],
        )
        self._run_check(
            "<?processing instruction ?>",
            [
                ("pi", "processing instruction ?"),
            ],
        )

    def test_simple_html(self):
        self._run_check(
            """
<!DOCTYPE html PUBLIC 'foo'>
<HTML>&entity;&#32;
<!--comment1a
-></foo><bar>&lt;<?pi?></foo<bar
comment1b-->
<Img sRc='Bar' isMAP>sample
text
&#x201C;
<!--comment2a-- --comment2b-->
</Html>
""",
            [
                ("data", "\n"),
                ("decl", "DOCTYPE html PUBLIC 'foo'"),
                ("data", "\n"),
                ("starttag", "HTML", "", []),
                ("entityref", "entity"),
                ("charref", "32"),
                ("data", "\n"),
                ("comment", "comment1a\n-></foo><bar>&lt;<?pi?></foo<bar\ncomment1b"),
                ("data", "\n"),
                ("starttag", "Img", "sRc='Bar' isMAP", []),
                ("data", "sample\ntext\n"),
                ("charref", "x201C"),
                ("data", "\n"),
                ("comment", "comment2a-- --comment2b"),
                ("data", "\n"),
                ("endtag", "Html"),
                ("data", "\n"),
            ],
        )

    def test_malformatted_charref(self):
        self._run_check(
            "<p>&#bad;</p>",
            [
                ("starttag", "p", "", []),
                ("data", "&#bad;"),
                ("endtag", "p"),
            ],
        )
        # add the [] as a workaround to avoid buffering (see #20288)
        self._run_check(
            ["<div>&#bad;</div>"],
            [
                ("starttag", "div", "", []),
                ("data", "&#bad;"),
                ("endtag", "div"),
            ],
        )

    def test_unclosed_entityref(self):
        self._run_check(
            "&entityref foo",
            [
                ("entityref", "entityref"),
                ("data", " foo"),
            ],
        )

    def test_bad_nesting(self):
        # Strangely, this *is* supposed to test that overlapping
        # elements are allowed.  Htp is more geared toward
        # lexing the input that parsing the structure.
        self._run_check(
            "<a><b></a></b>",
            [
                ("starttag", "a", "", []),
                ("starttag", "b", "", []),
                ("endtag", "a"),
                ("endtag", "b"),
            ],
        )

    def test_bare_ampersands(self):
        self._run_check(
            "this text & contains & ampersands &",
            [
                ("data", "this text & contains & ampersands &"),
            ],
        )

    def test_bare_pointy_brackets(self):
        self._run_check(
            "this < text > contains < bare>pointy< brackets",
            [
                ("data", "this < text > contains < bare>pointy< brackets"),
            ],
        )

    def test_starttag_end_boundary(self):
        self._run_check("""<a b='<'>""", [("starttag", "a", "b='<'", [])])
        self._run_check("""<a b='>'>""", [("starttag", "a", "b='>'", [])])
        self._run_check("""<a b='{{'>""", [("starttag", "a", "b='{{'", [])])
        self._run_check("""<a b='{%'>""", [("starttag", "a", "b='{%'", [])])
        self._run_check(
            """{% a b=<-%}""",
            [("starttag_curly_perc", "a", "b=<", ["spaceless-right-dash"])],
        )
        self._run_check("""{{ a %}}}""", [("curly_two", "a", "%", []), ("data", "}")])
        self._run_check(
            """{{{{ a <a }}}}>""",
            [("starttag_curly_four", "a", "<a", []), ("data", ">")],
        )
        self._run_check("""{{{ a <a }}}>""", [("curly_three", "a <a"), ("data", ">")])
        self._run_check(
            """{{~#if test {# wow #} }}""",
            [
                (
                    "starttag_curly_two_hash",
                    "if",
                    "test {# wow #}",
                    ["spaceless-left-tilde"],
                )
            ],
        )
        self._run_check(
            """\\{{escaped <a }}>""",
            [("slash_curly_two", "escaped", "<a"), ("data", ">")],
        )
        self._run_check(
            """{{#each {%}}%}""",
            [("starttag_curly_two_hash", "each", "{%", []), ("data", "%}")],
        )
        self._run_check("""@*<a*@>""", [("comment_at_star", "<a"), ("data", ">")])
        self._run_check("""{#<a#}>""", [("comment_curly_hash", "<a"), ("data", ">")])
        self._run_check(
            """{{!<a}}>""", [("comment_curly_exlaim", "<a", []), ("data", ">")]
        )
        self._run_check("""{{/<a}}>""", [("curly_two_slash", "<a", []), ("data", ">")])
        self._run_check(
            """{{{{/<a}}}}>""", [("endtag_curly_four", "<a", "", []), ("data", ">")]
        )
        self._run_check(
            """{{ "}}" }}""", [("curly_two", '"', "", []), ("data", '" }}')]
        )

    def test_buffer_artefacts(self):
        output = [("starttag", "a", "b='<'", [])]
        self._run_check(["<a b='<'>"], output)

        output = [("starttag", "a", "b='>'", [])]
        self._run_check(["<a b='>'>"], output)

        output = [("comment", "abc")]
        self._run_check(["<!--abc-->"], output)

    def test_valid_doctypes(self):
        # from http://www.w3.org/QA/2002/04/valid-dtd-list.html
        dtds = [
            "HTML",  # HTML5 doctype
            (
                'HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                '"http://www.w3.org/TR/html4/strict.dtd"'
            ),
            (
                'HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" '
                '"http://www.w3.org/TR/html4/loose.dtd"'
            ),
            (
                'html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
                '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"'
            ),
            (
                'html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" '
                '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd"'
            ),
            (
                'math PUBLIC "-//W3C//DTD MathML 2.0//EN" '
                '"http://www.w3.org/Math/DTD/mathml2/mathml2.dtd"'
            ),
            (
                'html PUBLIC "-//W3C//DTD '
                'XHTML 1.1 plus MathML 2.0 plus SVG 1.1//EN" '
                '"http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg.dtd"'
            ),
            (
                'svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
                '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"'
            ),
            'html PUBLIC "-//IETF//DTD HTML 2.0//EN"',
            'html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN"',
        ]
        for dtd in dtds:
            self._run_check("<!DOCTYPE %s>" % dtd, [("decl", "DOCTYPE " + dtd)])

    def test_startendtag(self):
        self._run_check(
            "<p/>",
            [
                ("startendtag", "p", "", ["is-selfclosing"]),
            ],
        )
        self._run_check(
            "<p></p>",
            [
                ("starttag", "p", "", []),
                ("endtag", "p"),
            ],
        )
        self._run_check(
            "<p><img src='foo' /></p>",
            [
                ("starttag", "p", "", []),
                ("startendtag", "img", "src='foo'", ["is-selfclosing"]),
                ("endtag", "p"),
            ],
        )

    def test_get_starttag_text(self):
        s = """<foo:bar   \n   one="1"\ttwo=2   >"""
        self._run_check_extra(
            s,
            [
                ("starttag", "foo:bar", 'one="1"\ttwo=2', []),
                ("starttag_text", '<foo:bar   \n   one="1"\ttwo=2   >'),
            ],
        )

    def test_cdata_content(self):
        contents = [
            "<!-- not a comment --> &not-an-entity-ref;",
            "<not a='start tag'>",
            '<a href="" /> <p> <span></span>',
            'foo = "</scr" + "ipt>";',
            'foo = "</SCRIPT" + ">";',
            "foo = <\n/script> ",
            '<!-- document.write("</scr" + "ipt>"); -->',
            (
                "\n//<![CDATA[\n"
                "document.write('<s'+'cript type=\"text/javascript\" "
                "src=\"http://www.example.org/r='+new "
                "Date().getTime()+'\"><\\/s'+'cript>');\n//]]>"
            ),
            "\n<!-- //\nvar foo = 3.14;\n// -->\n",
            'foo = "</sty" + "le>";',
            "<!-- \u2603 -->",
            # these two should be invalid according to the HTML 5 spec,
            # section 8.1.2.2
            #'foo = </\nscript>',
            #'foo = </ script>',
        ]
        elements = ["script", "style", "SCRIPT", "STYLE", "Script", "Style"]
        for content in contents:
            for element in elements:
                element_lower = element
                s = "<{element}>{content}</{element}>".format(
                    element=element, content=content
                )
                self._run_check(
                    s,
                    [
                        ("starttag", element_lower, "", []),
                        ("data", content),
                        ("endtag", element_lower),
                    ],
                )

    def test_cdata_more(self):
        html = (
            "<span><![CDATA[<sender>John Smith</sender>]]></span>\n"
            "<span><![CDATA[1]]> a <![CDATA[2]]></span>\n"
            "<span><![CDATA[1]]> <br> <![CDATA[2]]></span>\n"
        )
        expected = [
            ("starttag", "span", "", []),
            ("unknown decl", "CDATA[<sender>John Smith</sender>"),
            ("endtag", "span"),
            ("data", "\n"),
            ("starttag", "span", "", []),
            ("unknown decl", "CDATA[1"),
            ("data", " a "),
            ("unknown decl", "CDATA[2"),
            ("endtag", "span"),
            ("data", "\n"),
            ("starttag", "span", "", []),
            ("unknown decl", "CDATA[1"),
            ("data", " "),
            ("starttag", "br", "", []),
            ("data", " "),
            ("unknown decl", "CDATA[2"),
            ("endtag", "span"),
            ("data", "\n"),
        ]

        self._run_check(html, expected)

    def test_cdata_with_closing_tags(self):
        # see issue #13358
        # make sure that Htp calls handle_data only once for each CDATA.
        # The normal event collector normalizes  the events in get_events,
        # so we override it to return the original list of events.
        class Collector(EventCollector):
            def get_events(self):
                return self.events

        content = """<!-- not a comment --> &not-an-entity-ref;
                  <a href="" /> </p><p> <span></span></style>
                  '</script' + '>'"""
        for element in [
            " script",
            "script ",
            " script ",
            "\nscript",
            "script\n",
            "\nscript\n",
        ]:
            element_lower = element.strip()
            s = f"<script>{content}</{element}>"
            self._run_check(
                s,
                [
                    ("starttag", element_lower, "", []),
                    ("data", content),
                    ("endtag", element_lower),
                ],
                collector=Collector(convert_charrefs=False),
            )

    def test_comments(self):
        html = (
            "<!-- I'm a valid comment -->"
            "<!--me too!-->"
            "<!------>"
            "<!---->"
            "<!----I have many hyphens---->"
            "<!-- I have a > in the middle -->"
            "<!-- and I have -- in the middle! -->"
            "{# comment #}"
            "{% comment %} something?{%endcomment%}"
            '{% comment "asdf" %}no{%endcomment%}'
            "{{! handlebars are cool }}"
            "{{!-- even better }}"
            "@* razor *@"
        )
        expected = [
            ("comment", " I'm a valid comment "),
            ("comment", "me too!"),
            ("comment", "--"),
            ("comment", ""),
            ("comment", "--I have many hyphens--"),
            ("comment", " I have a > in the middle "),
            ("comment", " and I have -- in the middle! "),
            ("comment_curly_hash", " comment "),
            ("comment_curly_perc", "comment", "", []),
            ("data", " something?"),
            ("comment_curly_perc_close", "comment", []),
            ("comment_curly_perc", "comment", '"asdf"', []),
            ("data", "no"),
            ("comment_curly_perc_close", "comment", []),
            ("comment_curly_exlaim", " handlebars are cool ", []),
            ("comment_curly_exlaim", " even better ", ["safe-left"]),
            ("comment_at_star", " razor "),
        ]

        self._run_check(html, expected)

    def test_tag_curly_perc_if(self):
        html = "{% if this %}{% endif -%}"
        expected = [
            ("starttag_curly_perc", "if", "this", []),
            ("endtag_curly_perc", "if", "", ["spaceless-right-dash"]),
        ]
        self._run_check(html, expected)

    def test_tag_curly_perc_if_else(self):
        html = "{%- if this %}{%else -%}{% endif %}"
        expected = [
            ("starttag_curly_perc", "if", "this", ["spaceless-left-dash"]),
            ("starttag_curly_perc", "else", "", ["spaceless-right-dash"]),
            ("endtag_curly_perc", "if", "", []),
        ]
        self._run_check(html, expected)

    def test_curly_block(self):
        html = "{% block cool %}{% endblock cool%}"
        expected = [
            ("starttag_curly_perc", "block", "cool", []),
            ("endtag_curly_perc", "block", "cool", []),
        ]
        self._run_check(html, expected)

    def test_tag_curly_perc_for(self):
        html = "{% for x in range(0,10) %}{% endfor %}"
        expected = [
            ("starttag_curly_perc", "for", "x in range(0,10)", []),
            ("endtag_curly_perc", "for", "", []),
        ]
        self._run_check(html, expected)

        html = "{% for x in range(0,10) %}{{ x|length }}{% endfor %}"
        expected = [
            ("starttag_curly_perc", "for", "x in range(0,10)", []),
            ("curly_two", "x", "|length", []),
            ("endtag_curly_perc", "for", "", []),
        ]
        self._run_check(html, expected)

    def test_broken_curly(self):
        html = "{{ asdf}"
        expected = [
            ("data", "{{ asdf}"),
        ]
        self._run_check(html, expected)

        html = "{ asdf}}"
        expected = [
            ("data", "{ asdf}}"),
        ]
        self._run_check(html, expected)

    def test_condcoms(self):
        html = (
            "<!--[if IE & !(lte IE 8)]>aren't<![endif]-->"
            "<!--[if IE 8]>condcoms<![endif]-->"
            "<!--[if lte IE 7]>pretty?<![endif]-->"
        )
        expected = [
            ("comment", "[if IE & !(lte IE 8)]>aren't<![endif]"),
            ("comment", "[if IE 8]>condcoms<![endif]"),
            ("comment", "[if lte IE 7]>pretty?<![endif]"),
        ]
        self._run_check(html, expected)

    def test_convert_charrefs(self):
        # default value for convert_charrefs is now True
        collector = lambda: EventCollectorCharrefs()  # noqa: E731
        self.assertTrue(collector().convert_charrefs)
        charrefs = ["&quot;", "&#34;", "&#x22;", "&quot", "&#34", "&#x22"]
        # check charrefs in the middle of the text/attributes

        for charref in charrefs:
            expected = [
                ("starttag", "a", f'href="foo{charref}zar"', []),
                ("data", 'a"z'),
                ("endtag", "a"),
            ]
            self._run_check(
                '<a href="foo{0}zar">a{0}z</a>'.format(charref),
                expected,
                collector=collector(),
            )
        # check charrefs at the beginning/end of the text/attributes

        for charref in charrefs:
            expected = [
                ("data", '"'),
                ("starttag", "a", f'x="{charref}" y="{charref}X" z="X{charref}"', []),
                ("data", '"'),
                ("endtag", "a"),
                ("data", '"'),
            ]
            self._run_check(
                '{0}<a x="{0}" y="{0}X" z="X{0}">' "{0}</a>{0}".format(charref),
                expected,
                collector=collector(),
            )
        # check charrefs in <script>/<style> elements
        for charref in charrefs:
            text = "X".join([charref] * 3)
            expected = [
                ("data", '"'),
                ("starttag", "script", "", []),
                ("data", text),
                ("endtag", "script"),
                ("data", '"'),
                ("starttag", "style", "", []),
                ("data", text),
                ("endtag", "style"),
                ("data", '"'),
            ]
            self._run_check(
                "{1}<script>{0}</script>{1}"
                "<style>{0}</style>{1}".format(text, charref),
                expected,
                collector=collector(),
            )
        # check truncated charrefs at the end of the file
        html = "&quo &# &#x"
        for x in range(1, len(html)):
            self._run_check(html[:x], [("data", html[:x])], collector=collector())
        # check a string with no charrefs
        self._run_check(
            "no charrefs here", [("data", "no charrefs here")], collector=collector()
        )

    # the remaining tests were for the "tolerant" parser (which is now
    # the default), and check various kind of broken markup
    def test_tolerant_parsing(self):
        self._run_check(
            "<html <html>te>>xt&a<<bc</a></html>\n"
            '<img src="URL><//img></html</html>',
            [
                ("starttag", "html", "<html", []),
                ("data", "te>>xt"),
                ("entityref", "a"),
                ("data", "<"),
                ("starttag", "bc<", "/a", []),
                ("endtag", "html"),
                ("data", "\n"),
                ("starttag", "img", 'src="URL', []),
                ("comment", "/img"),
                ("endtag", "html<"),
            ],
        )

    def test_starttag_junk_chars(self):
        self._run_check("</>", [])
        self._run_check("</$>", [("comment", "$")])
        self._run_check("</", [("data", "</")])
        self._run_check("</a", [("data", "</a")])
        self._run_check("<a<a>", [("starttag", "a<a", "", [])])
        self._run_check("</a<a>", [("endtag", "a<a")])
        self._run_check("<!", [("data", "<!")])
        self._run_check("<a", [("data", "<a")])
        self._run_check("<a foo='bar'", [("data", "<a foo='bar'")])
        self._run_check("<a foo='bar", [("data", "<a foo='bar")])
        self._run_check("<a foo='>'", [("data", "<a foo='>'")])
        self._run_check("<a foo='>", [("starttag", "a", "foo='", [])])
        self._run_check("<a$>", [("starttag", "a$", "", [])])
        self._run_check("<a$b>", [("starttag", "a$b", "", [])])
        self._run_check("<a$b/>", [("startendtag", "a$b", "", ["is-selfclosing"])])
        self._run_check("<a$b  >", [("starttag", "a$b", "", [])])
        self._run_check("<a$b  />", [("startendtag", "a$b", "", ["is-selfclosing"])])

    def test_slashes_in_starttag(self):
        self._run_check(
            '<a foo="var"/>', [("startendtag", "a", 'foo="var"', ["is-selfclosing"])]
        )
        html = (
            "<img width=902 height=250px "
            'src="/sites/default/files/images/homepage/foo.jpg" '
            "/*what am I doing here*/ />"
        )
        expected = [
            (
                "startendtag",
                "img",
                'width=902 height=250px src="/sites/default/files/images/homepage/foo.jpg" '
                "/*what am I doing here*/",
                ["is-selfclosing"],
            )
        ]
        self._run_check(html, expected)
        html = "<a / /foo/ / /=/ / /bar/ / />" "<a / /foo/ / /=/ / /bar/ / >"
        expected = [
            ("startendtag", "a", "/ /foo/ / /=/ / /bar/ /", ["is-selfclosing"]),
            ("starttag", "a", "/ /foo/ / /=/ / /bar/ /", []),
        ]
        self._run_check(html, expected)
        # see issue #14538
        html = "<meta><meta / ><meta // ><meta / / >" "<meta/><meta /><meta //><meta//>"
        expected = [
            ("starttag", "meta", "", []),
            ("starttag", "meta", "/", []),
            ("starttag", "meta", "//", []),
            ("starttag", "meta", "/ /", []),
            ("startendtag", "meta", "", ["is-selfclosing"]),
            ("startendtag", "meta", "", ["is-selfclosing"]),
            ("startendtag", "meta", "/", ["is-selfclosing"]),
            ("startendtag", "meta", "/", ["is-selfclosing"]),
        ]
        self._run_check(html, expected)

    def test_declaration_junk_chars(self):
        self._run_check("<!DOCTYPE foo $ >", [("decl", "DOCTYPE foo $ ")])

    def test_illegal_declarations(self):
        self._run_check(
            '<!spacer type="block" height="25">',
            [("comment", 'spacer type="block" height="25"')],
        )

    def test_invalid_end_tags(self):
        # A collection of broken end tags. <br> is used as separator.
        # see http://www.w3.org/TR/html5/tokenization.html#end-tag-open-state
        # and #13993
        html = (
            "<br></label</p><br></div end tmAd-leaderBoard><br></<h4><br>"
            '</li class="unit"><br></li\r\n\t\t\t\t\t\t</ul><br></><br>'
        )
        expected = [
            ("starttag", "br", "", []),
            # < is part of the name, / is discarded, p is an attribute
            ("endtag", "label<"),
            ("starttag", "br", "", []),
            # text and attributes are discarded
            ("endtag", "div"),
            ("starttag", "br", "", []),
            # comment because the first char after </ is not a-zA-Z
            ("comment", "<h4"),
            ("starttag", "br", "", []),
            # attributes are discarded
            ("endtag", "li"),
            ("starttag", "br", "", []),
            # everything till ul (included) is discarded
            ("endtag", "li"),
            ("starttag", "br", "", []),
            # </> is ignored
            ("starttag", "br", "", []),
        ]
        self._run_check(html, expected)

    def test_broken_invalid_end_tag(self):
        # This is technically wrong (the "> shouldn't be included in the 'data')
        # but is probably not worth fixing it (in addition to all the cases of
        # the previous test, it would require a full attribute parsing).
        # see #13993
        html = '<b>This</b attr=">"> confuses the parser'
        expected = [
            ("starttag", "b", "", []),
            ("data", "This"),
            ("endtag", "b"),
            ("data", '"> confuses the parser'),
        ]
        self._run_check(html, expected)

    def test_correct_detection_of_start_tags(self):
        # see #13273
        html = (
            '<div style=""    ><b>The <a href="some_url">rain</a> '
            "<br /> in <span>Spain</span></b></div>"
        )
        expected = [
            ("starttag", "div", 'style=""', []),
            ("starttag", "b", "", []),
            ("data", "The "),
            ("starttag", "a", 'href="some_url"', []),
            ("data", "rain"),
            ("endtag", "a"),
            ("data", " "),
            ("startendtag", "br", "", ["is-selfclosing"]),
            ("data", " in "),
            ("starttag", "span", "", []),
            ("data", "Spain"),
            ("endtag", "span"),
            ("endtag", "b"),
            ("endtag", "div"),
        ]
        self._run_check(html, expected)

        html = '<div style="", foo = "bar" ><b>The <a href="some_url">rain</a>'
        expected = [
            ("starttag", "div", 'style="", foo = "bar"', []),
            ("starttag", "b", "", []),
            ("data", "The "),
            ("starttag", "a", 'href="some_url"', []),
            ("data", "rain"),
            ("endtag", "a"),
        ]
        self._run_check(html, expected)

    def test_EOF_in_charref(self):
        # see #17802
        # This test checks that the UnboundLocalError reported in the issue
        # is not raised, however I'm not sure the returned values are correct.
        # Maybe Htp should use self.unescape for these
        data = [
            ("a&", [("data", "a&")]),
            ("a&b", [("data", "ab")]),
            ("a&b ", [("data", "a"), ("entityref", "b"), ("data", " ")]),
            ("a&b;", [("data", "a"), ("entityref", "b")]),
        ]
        for html, expected in data:
            self._run_check(html, expected)

    def test_broken_comments(self):
        html = (
            "<! not really a comment >"
            "<! not a comment either -->"
            "<! -- close enough -->"
            "<!><!<-- this was an empty comment>"
            "<!!! another bogus comment !!!>"
        )
        expected = [
            ("comment", " not really a comment "),
            ("comment", " not a comment either --"),
            ("comment", " -- close enough --"),
            ("comment", ""),
            ("comment", "<-- this was an empty comment"),
            ("comment", "!! another bogus comment !!!"),
        ]
        self._run_check(html, expected)

    def test_broken_condcoms(self):
        # these condcoms are missing the '--' after '<!' and before the '>'
        html = (
            "<![if !(IE)]>broken condcom<![endif]>"
            '<![if ! IE]><link href="favicon.tiff"/><![endif]>'
            '<![if !IE 6]><img src="firefox.png" /><![endif]>'
            "<![if !ie 6]><b>foo</b><![endif]>"
            '<![if (!IE)|(lt IE 9)]><img src="mammoth.bmp" /><![endif]>'
        )
        # According to the HTML5 specs sections "8.2.4.44 Bogus comment state"
        # and "8.2.4.45 Markup declaration open state", comment tokens should
        # be emitted instead of 'unknown decl', but calling unknown_decl
        # provides more flexibility.
        # See also Lib/_markupbase.py:parse_declaration
        expected = [
            ("unknown decl", "if !(IE)"),
            ("data", "broken condcom"),
            ("unknown decl", "endif"),
            ("unknown decl", "if ! IE"),
            ("startendtag", "link", 'href="favicon.tiff"', ["is-selfclosing"]),
            ("unknown decl", "endif"),
            ("unknown decl", "if !IE 6"),
            ("startendtag", "img", 'src="firefox.png"', ["is-selfclosing"]),
            ("unknown decl", "endif"),
            ("unknown decl", "if !ie 6"),
            ("starttag", "b", "", []),
            ("data", "foo"),
            ("endtag", "b"),
            ("unknown decl", "endif"),
            ("unknown decl", "if (!IE)|(lt IE 9)"),
            ("startendtag", "img", 'src="mammoth.bmp"', ["is-selfclosing"]),
            ("unknown decl", "endif"),
        ]
        self._run_check(html, expected)

    def test_convert_charrefs_dropped_text(self):
        # #23144: make sure that all the events are triggered when
        # convert_charrefs is True, even if we don't call .close()
        parser = EventCollector(convert_charrefs=True)
        # before the fix, bar & baz was missing
        parser.feed("foo <a>link</a> bar &amp; baz")
        self.assertEqual(
            parser.get_events(),
            [
                ("data", "foo "),
                ("starttag", "a", "", []),
                ("data", "link"),
                ("endtag", "a"),
                ("data", " bar & baz"),
            ],
        )

    def test_template_tags(self):
        self._run_check("{# comment #}", [("comment_curly_hash", " comment ")])
        self._run_check("{{{ stuff }}}", [("curly_three", "stuff")])

    def test_handlebars_escape(self):
        self._run_check(
            r"""
            \{{escaped attr}}
{{{{raw}}}}
  {{escaped}}data-src={%-url "tag:tag" pk=a.B.c 123    -%}
{{{{/raw}}}}""",
            [
                ("data", "\n            "),
                ("slash_curly_two", "escaped", "attr"),
                ("data", "\n"),
                ("starttag_curly_four", "raw", "", []),
                ("data", "\n  "),
                ("curly_two", "escaped", "", []),
                ("data", "data-src="),
                (
                    "starttag_curly_perc",
                    "url",
                    '"tag:tag" pk=a.B.c 123',
                    ["spaceless-left-dash", "spaceless-right-dash"],
                ),
                ("data", "\n"),
                ("endtag_curly_four", "raw", "", []),
            ],
        )

    def test_handlebars_if(self):
        self._run_check(
            """
            {{#if test}}
      {{title}}
    {{^}}
      Empty
    {{/if}}""",
            [
                ("data", "\n            "),
                ("starttag_curly_two_hash", "if", "test", []),
                ("data", "\n      "),
                ("curly_two", "title", "", []),
                ("data", "\n    "),
                ("curly_two", "^", "", []),
                ("data", "\n      Empty\n    "),
                ("curly_two_slash", "if", []),
            ],
        )

    def test_handlebars_whitespace_control(self):
        self._run_check(
            """
            {{~#if test}}
      {{~title}}
    {{~^~}}
      Empty
    {{~/if~}}
            """,
            [
                ("data", "\n            "),
                ("starttag_curly_two_hash", "if", "test", ["spaceless-left-tilde"]),
                ("data", "\n      "),
                ("curly_two", "title", "", ["spaceless-left-tilde"]),
                ("data", "\n    "),
                (
                    "curly_two",
                    "^",
                    "",
                    ["spaceless-left-tilde", "spaceless-right-tilde"],
                ),
                ("data", "\n      Empty\n    "),
                (
                    "curly_two_slash",
                    "if",
                    ["spaceless-left-tilde", "spaceless-right-tilde"],
                ),
                ("data", "\n            "),
            ],
        )

    def test_handlebars_each(self):
        self._run_check(
            """
            {{#each people}}
    {{../prefix}} {{firstname}}
{{/each}}
            """,
            [
                ("data", "\n            "),
                ("starttag_curly_two_hash", "each", "people", []),
                ("data", "\n    "),
                ("curly_two", "../prefix", "", []),
                ("data", " "),
                ("curly_two", "firstname", "", []),
                ("data", "\n"),
                ("curly_two_slash", "each", []),
                ("data", "\n            "),
            ],
        )

    def test_handlebars_expressions(self):
        self._run_check(
            """
            {{person.firstname}} {{person.lastname}}
            """,
            [
                ("data", "\n            "),
                ("curly_two", "person.firstname", "", []),
                ("data", " "),
                ("curly_two", "person.lastname", "", []),
                ("data", "\n            "),
            ],
        )

    def test_handlebars_special_char(self):
        self._run_check(
            """
            {{{specialChars}}}
            """,
            [
                ("data", "\n            "),
                ("curly_three", "specialChars"),
                ("data", "\n            "),
            ],
        )

    def test_handlebars_attributes(self):
        self._run_check(
            """
            {{loud lastname}}
            """,
            [
                ("data", "\n            "),
                ("curly_two", "loud", "lastname", []),
                ("data", "\n            "),
            ],
        )

    def test_set(self):
        self._run_check(
            """
            {% set cool=[{loud:"lastname"}] %}
            """,
            [
                ("data", "\n            "),
                ("starttag_curly_perc", "set", 'cool=[{loud:"lastname"}]', []),
                ("data", "\n            "),
            ],
        )

    def test_bad_stuff(self):
        self._run_check("{% {{ ok }}", [("data", "{% "), ("curly_two", "ok", "", [])])
        self._run_check(
            "{# {% ok %}", [("data", "{# "), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "{{ {% ok %}", [("data", "{{ "), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "{{! {% ok %}", [("data", "{{! "), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "@* {% ok %}", [("data", "@* "), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "{{# {% ok %}", [("data", "{{# "), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "{{/ {% ok %}", [("data", "{{/ "), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "\\{{ {% ok %}",
            [("data", "\\{{ "), ("starttag_curly_perc", "ok", "", [])],
        )
        self._run_check(
            "{{{ {% ok %}", [("data", "{{{ "), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "{{{{ {% ok %}",
            [("data", "{{{{ "), ("starttag_curly_perc", "ok", "", [])],
        )
        self._run_check(
            "{{{{/ {% ok %}",
            [("data", "{{{{/ "), ("starttag_curly_perc", "ok", "", [])],
        )
        self._run_check(
            '" {% ok %}', [("data", '" '), ("starttag_curly_perc", "ok", "", [])]
        )
        self._run_check(
            "' {% ok %}", [("data", "' "), ("starttag_curly_perc", "ok", "", [])]
        )

    def test_partial(self):
        self._run_check(
            "{{> myPartial }}", [("curly_two", "myPartial", "", ["partial"])]
        )
        self._run_check(
            "{{> (whichPartial) }}", [("curly_two", "(whichPartial)", "", ["partial"])]
        )
        self._run_check(
            "{{> (lookup . 'myVariable') }}",
            [("curly_two", "(lookup", ". 'myVariable')", ["partial"])],
        )
        self._run_check(
            "{{> myPartial myOtherContext }}",
            [("curly_two", "myPartial", "myOtherContext", ["partial"])],
        )
        self._run_check(
            "{{> myPartial parameter=favoriteNumber }}",
            [("curly_two", "myPartial", "parameter=favoriteNumber", ["partial"])],
        )
        self._run_check(
            """{{#each people}}
  {{> myPartial prefix=../prefix firstname=firstname lastname=lastname}}.
{{/each}}""",
            [
                ("starttag_curly_two_hash", "each", "people", []),
                ("data", "\n  "),
                (
                    "curly_two",
                    "myPartial",
                    "prefix=../prefix firstname=firstname lastname=lastname",
                    ["partial"],
                ),
                ("data", ".\n"),
                ("curly_two_slash", "each", []),
            ],
        )
        self._run_check(
            """{{#> myPartial }}
  Failover content
{{/myPartial}}""",
            [
                ("starttag_curly_two_hash", "myPartial", "", ["partial"]),
                ("data", "\n  Failover content\n"),
                ("curly_two_slash", "myPartial", []),
            ],
        )

        self._run_check(
            """{{#each people as |person|}}
  {{#> childEntry}}
    {{person.firstname}}
  {{/childEntry}}
{{/each}}""",
            [
                ("starttag_curly_two_hash", "each", "people as |person|", []),
                ("data", "\n  "),
                ("starttag_curly_two_hash", "childEntry", "", ["partial"]),
                ("data", "\n    "),
                ("curly_two", "person.firstname", "", []),
                ("data", "\n  "),
                ("curly_two_slash", "childEntry", []),
                ("data", "\n"),
                ("curly_two_slash", "each", []),
            ],
        )

        self._run_check(
            """{{#*inline "myPartial"}}
  My Content
{{/inline}}
{{#each people}}
  {{> myPartial}}
{{/each}}""",
            [
                ("starttag_curly_two_hash", "*inline", '"myPartial"', []),
                ("data", "\n  My Content\n"),
                ("curly_two_slash", "inline", []),
                ("data", "\n"),
                ("starttag_curly_two_hash", "each", "people", []),
                ("data", "\n  "),
                ("curly_two", "myPartial", "", ["partial"]),
                ("data", "\n"),
                ("curly_two_slash", "each", []),
            ],
        )


class AttributesTestCase(TestCaseBase):
    # no attribute parsing happens here. all should be matching the input string.
    def test_attr_syntax(self):

        self._run_check(
            """<a b='v' c="v" d=v e>""", [("starttag", "a", "b='v' c=\"v\" d=v e", [])]
        )
        self._run_check(
            """<a  b = 'v' c = "v" d = v e>""",
            [("starttag", "a", "b = 'v' c = \"v\" d = v e", [])],
        )
        self._run_check(
            """<a\nb\n=\n'v'\nc\n=\n"v"\nd\n=\nv\ne>""",
            [("starttag", "a", "b\n=\n'v'\nc\n=\n\"v\"\nd\n=\nv\ne", [])],
        )
        self._run_check(
            """<a\tb\t=\t'v'\tc\t=\t"v"\td\t=\tv\te>""",
            [("starttag", "a", "b\t=\t'v'\tc\t=\t\"v\"\td\t=\tv\te", [])],
        )

    def test_attr_values(self):
        self._run_check(
            """<a b='xxx\n\txxx' c="yyy\t\nyyy" d='\txyz\n'>""",
            [("starttag", "a", "b='xxx\n\txxx' c=\"yyy\t\nyyy\" d='\txyz\n'", [])],
        )
        self._run_check("""<a b='' c="">""", [("starttag", "a", "b='' c=\"\"", [])])
        # Regression test for SF patch #669683.
        self._run_check("<e a=rgb(1,2,3)>", [("starttag", "e", "a=rgb(1,2,3)", [])])
        # Regression test for SF bug #921657.
        self._run_check(
            "<a href=mailto:xyz@example.com>",
            [("starttag", "a", "href=mailto:xyz@example.com", [])],
        )

    def test_attr_nonascii(self):
        # see issue 7311
        self._run_check(
            "<img src=/foo/bar.png alt=\u4e2d\u6587>",
            [("starttag", "img", "src=/foo/bar.png alt=\u4e2d\u6587", [])],
        )
        self._run_check(
            "<a title='\u30c6\u30b9\u30c8' href='\u30c6\u30b9\u30c8.html'>",
            [
                (
                    "starttag",
                    "a",
                    "title='\u30c6\u30b9\u30c8' href='\u30c6\u30b9\u30c8.html'",
                    [],
                )
            ],
        )
        self._run_check(
            '<a title="\u30c6\u30b9\u30c8" href="\u30c6\u30b9\u30c8.html">',
            [
                (
                    "starttag",
                    "a",
                    'title="\u30c6\u30b9\u30c8" href="\u30c6\u30b9\u30c8.html"',
                    [],
                )
            ],
        )

    def test_attr_entity_replacement(self):
        self._run_check(
            "<a b='&amp;&gt;&lt;&quot;&apos;'>",
            [("starttag", "a", "b='&amp;&gt;&lt;&quot;&apos;'", [])],
        )

    def test_attr_funky_names(self):
        self._run_check(
            "<a a.b='v' c:d=v e-f=v>", [("starttag", "a", "a.b='v' c:d=v e-f=v", [])]
        )

    def test_entityrefs_in_attributes(self):
        self._run_check(
            "<html foo='&euro;&amp;&#97;&#x61;&unsupported;'>",
            [("starttag", "html", "foo='&euro;&amp;&#97;&#x61;&unsupported;'", [])],
        )

    def test_attr_funky_names2(self):
        self._run_check(
            r"<a $><b $=%><c \=/>",
            [
                ("starttag", "a", "$", []),
                ("starttag", "b", "$=%", []),
                ("starttag", "c", "\\=/", []),
            ],
        )

    def test_entities_in_attribute_value(self):
        # see #1200313
        for entity in ["&", "&amp;", "&#38;", "&#x26;"]:
            self._run_check(
                '<a href="%s">' % entity, [("starttag", "a", f'href="{entity}"', [])]
            )
            self._run_check(
                "<a href='%s'>" % entity, [("starttag", "a", f"href='{entity}'", [])]
            )
            self._run_check(
                "<a href=%s>" % entity, [("starttag", "a", f"href={entity}", [])]
            )

    def test_malformed_attributes(self):
        # see #13357
        html = (
            "<a href=test'style='color:red;bad1'>test - bad1</a>"
            "<a href=test'+style='color:red;ba2'>test - bad2</a>"
            "<a href=test'&nbsp;style='color:red;bad3'>test - bad3</a>"
            "<a href = test'&nbsp;style='color:red;bad4'  >test - bad4</a>"
        )
        expected = [
            ("starttag", "a", "href=test'style='color:red;bad1'", []),
            ("data", "test - bad1"),
            ("endtag", "a"),
            ("starttag", "a", "href=test'+style='color:red;ba2'", []),
            ("data", "test - bad2"),
            ("endtag", "a"),
            ("starttag", "a", "href=test'&nbsp;style='color:red;bad3'", []),
            ("data", "test - bad3"),
            ("endtag", "a"),
            ("starttag", "a", "href = test'&nbsp;style='color:red;bad4'", []),
            ("data", "test - bad4"),
            ("endtag", "a"),
        ]
        self._run_check(html, expected)

    def test_malformed_adjacent_attributes(self):
        # see #12629
        self._run_check(
            '<x><y z=""o"" /></x>',
            [
                ("starttag", "x", "", []),
                ("startendtag", "y", 'z=""o""', ["is-selfclosing"]),
                ("endtag", "x"),
            ],
        )
        self._run_check(
            '<x><y z="""" /></x>',
            [
                ("starttag", "x", "", []),
                ("startendtag", "y", 'z=""""', ["is-selfclosing"]),
                ("endtag", "x"),
            ],
        )

    # see #755670 for the following 3 tests
    def test_adjacent_attributes(self):
        self._run_check(
            '<a width="100%"cellspacing=0>',
            [("starttag", "a", 'width="100%"cellspacing=0', [])],
        )

        self._run_check(
            '<a id="foo"class="bar">', [("starttag", "a", 'id="foo"class="bar"', [])]
        )

    def test_missing_attribute_value(self):
        self._run_check("<a v=>", [("starttag", "a", "v=", [])])

    def test_javascript_attribute_value(self):
        self._run_check(
            "<a href=javascript:popup('/popup/help.html')>",
            [("starttag", "a", "href=javascript:popup('/popup/help.html')", [])],
        )

    def test_end_tag_in_attribute_value(self):
        # see #1745761
        self._run_check(
            "<a href='http://www.example.org/\">;'>spam</a>",
            [
                ("starttag", "a", "href='http://www.example.org/\">;'", []),
                ("data", "spam"),
                ("endtag", "a"),
            ],
        )

    def test_with_unquoted_attributes(self):
        # see #12008
        html = (
            "<html><body bgcolor=d0ca90 text='181008'>"
            "<table cellspacing=0 cellpadding=1 width=100% ><tr>"
            "<td align=left><font size=-1>"
            "- <a href=/rabota/><span class=en> software-and-i</span></a>"
            "- <a href='/1/'><span class=en> library</span></a></table>"
        )
        expected = [
            ("starttag", "html", "", []),
            ("starttag", "body", "bgcolor=d0ca90 text='181008'", []),
            ("starttag", "table", "cellspacing=0 cellpadding=1 width=100%", []),
            ("starttag", "tr", "", []),
            ("starttag", "td", "align=left", []),
            ("starttag", "font", "size=-1", []),
            ("data", "- "),
            ("starttag", "a", "href=/rabota/", []),
            ("starttag", "span", "class=en", []),
            ("data", " software-and-i"),
            ("endtag", "span"),
            ("endtag", "a"),
            ("data", "- "),
            ("starttag", "a", "href='/1/'", []),
            ("starttag", "span", "class=en", []),
            ("data", " library"),
            ("endtag", "span"),
            ("endtag", "a"),
            ("endtag", "table"),
        ]
        self._run_check(html, expected)

    def test_comma_between_attributes(self):
        # see bpo 41478
        # Htp preserves duplicate attributes, leaving the task of
        # removing duplicate attributes to a conformant html tree builder
        html = (
            "<div class=bar,baz=asd>"  # between attrs (unquoted)
            '<div class="bar",baz="asd">'  # between attrs (quoted)
            "<div class=bar, baz=asd,>"  # after values (unquoted)
            '<div class="bar", baz="asd",>'  # after values (quoted)
            '<div class="bar",>'  # one comma values (quoted)
            "<div class=,bar baz=,asd>"  # before values (unquoted)
            '<div class=,"bar" baz=,"asd">'  # before values (quoted)
            "<div ,class=bar ,baz=asd>"  # before names
            '<div class,="bar" baz,="asd">'  # after names
        )
        expected = [
            ("starttag", "div", "class=bar,baz=asd", []),
            ("starttag", "div", 'class="bar",baz="asd"', []),
            ("starttag", "div", "class=bar, baz=asd,", []),
            ("starttag", "div", 'class="bar", baz="asd",', []),
            ("starttag", "div", 'class="bar",', []),
            ("starttag", "div", "class=,bar baz=,asd", []),
            ("starttag", "div", 'class=,"bar" baz=,"asd"', []),
            ("starttag", "div", ",class=bar ,baz=asd", []),
            ("starttag", "div", 'class,="bar" baz,="asd"', []),
        ]
        self._run_check(html, expected)

    def test_weird_chars_in_unquoted_attribute_values(self):
        self._run_check(
            "<form action=bogus|&#()value>",
            [("starttag", "form", "action=bogus|&#()value", [])],
        )


if __name__ == "__main__":
    unittest.main()
