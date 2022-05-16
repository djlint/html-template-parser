<h1 align="center">HTML Template Parser</h1>

<h4 align="center">Modified version of Python's HTMLParser for HTML template parsing</h4>

<p align="center">
  <a href="https://codecov.io/gh/Riverside-Healthcare/html-template-parser">
    <img src="https://codecov.io/gh/Riverside-Healthcare/html-template-parser/branch/master/graph/badge.svg?token=Chqq9Mai1h"/>
  </a>
  <a href="https://github.com/Riverside-Healthcare/html-template-parser/actions/workflows/test.yml">
    <img src="https://github.com/Riverside-Healthcare/html-template-parser/actions/workflows/test.yml/badge.svg" alt="Test Status">
  </a>
  <a href="https://www.codacy.com/gh/Riverside-Healthcare/html-template-parser/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Riverside-Healthcare/html-template-parser&amp;utm_campaign=Badge_Grade">
    <img src="https://app.codacy.com/project/badge/Grade/43736e5b780a49d88d8ce588f5cfb9bc"/>
  </a>
  <a href="https://pepy.tech/project/html-template-parser">
    <img src="https://static.pepy.tech/badge/html-template-parser" alt="Downloads">
  </a>
  <a href="https://pypi.org/project/html-template-parser/">
    <img src="https://badgen.net/pypi/v/html-template-parser" alt="Pypi Version">
  </a>
</p>

## 🤔 For What?

The is an HTML template parser. It is a modified version of Python's HTMLParse library, expanded to handle template tags.


## 💾 Install

```sh
pip install html-template-parser

# or

poetry add html-template-parser
```

## ✨ How to Use

A basic usage example is remarkably similar to Python's HTMLParser:

```py
from HtmlTemplateParser import Htp

class MyHTMLParser(Htp):
    def handle_starttag(self, tag, attrs):
        print("Encountered a start tag:", tag)

    def handle_endtag(self, tag):
        print("Encountered an end tag :", tag)

    def handle_data(self, data):
        print("Encountered some data  :", data)

parser = MyHTMLParser()
parser.feed('<html><head><title>Test</title></head>'
            '<body><h1>Parse me!</h1></body></html>')

```
