"""Tests for Htp.

Many tests are from python's HTMLParse library, expanded to include
html template parsing.

See Python's license: https://github.com/python/cpython/blob/main/LICENSE

https://github.com/python/cpython/blob/f4c03484da59049eb62a9bf7777b963e2267d187/Lib/test/test_htmlparser.py

"""
# pylint: disable=C0115,W0237,E1101,W0108,W1404,C3001,W0613

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
        self.append((self.getpos(), self.get_element_text()))

    def handle_starttag_curly_perc(self, tag, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_starttag_curly_two_hash(self, tag, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_starttag_curly_four(self, tag, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_startendtag(self, tag, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_endtag(self, tag):
        self.append((self.getpos(), self.get_element_text()))

    def handle_endtag_curly_perc(self, tag, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_endtag_curly_hash(self, tag):
        self.append((self.getpos(), self.get_element_text()))

    def handle_endtag_curly_four_slash(self, tag, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_curly_two(self, data, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_slash_curly_two(self, data, attrs):
        self.append((self.getpos(), self.get_element_text()))

    def handle_curly_three(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_endtag_curly_two_slash(self, tag, props):
        self.append((self.getpos(), self.get_element_text()))

    # all other markup

    def handle_comment(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_comment_curly_hash(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_comment_curly_two_exlaim(self, data, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_comment_at_star(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_starttag_comment_curly_perc(self, data, attrs, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_endtag_comment_curly_perc(self, data, props):
        self.append((self.getpos(), self.get_element_text()))

    def handle_charref(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_data(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_decl(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_entityref(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def handle_pi(self, data):
        self.append((self.getpos(), self.get_element_text()))

    def unknown_decl(self, decl):
        self.append((self.getpos(), self.get_element_text()))


class EventCollectorExtra(EventCollector):
    def handle_starttag(self, tag, attrs, props):
        EventCollector.handle_starttag(self, tag, attrs, props)
        self.append((self.getpos(), self.get_element_text()))


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


class HtpTestCase(TestCaseBase):
    def test_tags(self):

        tags = [
            "<div <asdf'>",
            "</div>",
            "<br />",
            "{% if %}",
            "<!-- comment -->",
            "{# comment #}",
            "{{#>each}}",
            "{{/each}}",
            "{{{escaped}}}",
            "{{{{~raw}}}}",
            "{{{{/raw~}}}}",
            "\\{{escaped}}",
            "{{!comment}}",
            "<!DOCTYPE html PUBLIC 'foo'>",
            "&entity;",
            "&#32;",
            "<Img sRc='Bar' isMAP>",
            "{{^}}",
            "{{title}}",
            "{{~#if test}}",
            "{{~title}}",
            "Empty",
            '{% set cool=[{loud:"lastname"}] %}',
            '{{#*inline "myPartial"}}',
            "{%+ with x = b %}",
            "{{!-- wow--}}",
            "{",
        ]

        for tag in tags:

            self._run_check(
                tag,
                [
                    ((1, 0), tag),
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
                ((1, 0), "\n"),
                ((2, 0), "<!DOCTYPE html PUBLIC 'foo'>"),
                ((2, 28), "\n"),
                ((3, 0), "<HTML>"),
                ((3, 6), "&entity;"),
                ((3, 14), "&#32;"),
                ((3, 19), "\n"),
                (
                    (4, 0),
                    "<!--comment1a\n-></foo><bar>&lt;<?pi?></foo<bar\ncomment1b-->",
                ),
                ((6, 12), "\n"),
                ((7, 0), "<Img sRc='Bar' isMAP>"),
                ((7, 21), "sample\ntext\n"),
                ((9, 0), "&#x201C;"),
                ((9, 8), "\n"),
                ((10, 0), "<!--comment2a-- --comment2b-->"),
                ((10, 30), "\n"),
                ((11, 0), "</Html>"),
                ((11, 7), "\n"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
