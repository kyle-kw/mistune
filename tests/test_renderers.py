from unittest import TestCase

from mistune import BlockState, HTMLRenderer, create_markdown
from mistune.renderers.markdown import MarkdownRenderer
from mistune.renderers.rst import RSTRenderer
from tests import BaseTestCase


def load_renderer(renderer):
    class TestRenderer(BaseTestCase):
        parse = create_markdown(renderer=renderer)

    name = renderer.NAME
    TestRenderer.load_fixtures("renderer_" + name + ".txt")
    globals()["TestRenderer" + name.title()] = TestRenderer


load_renderer(RSTRenderer())
load_renderer(MarkdownRenderer())


class TestMarkdownRendererRoundTrip(TestCase):
    """Reformatting valid Markdown must not change its meaning: rendering the
    reformatted source to HTML must match rendering the original source."""

    to_html = create_markdown(escape=False)
    reformat = create_markdown(renderer=MarkdownRenderer())

    def assert_round_trip(self, text):
        self.assertEqual(
            self.to_html(self.reformat(text)),
            self.to_html(text),
        )

    def test_escaped_block_markers(self):
        # an escaped leading marker is literal text, not a new block
        for marker in (r"\*", r"\-", r"\+", r"\#", r"\##", r"\>", r"1\.", r"3\)"):
            self.assert_round_trip(marker + " literal\n")

    def test_escaped_marker_on_continuation_line(self):
        self.assert_round_trip("paragraph\n\\* not a list\n")

    def test_escaped_marker_inside_list_item(self):
        self.assert_round_trip("- item\n\n  \\# not a heading\n")

    def test_escaped_backtick(self):
        self.assert_round_trip(r"\`not code\`" + "\n")

    def test_literal_brackets_not_reparsed_as_links_or_images(self):
        for text in (
            r"Use \[draft\](report.txt) for details.",
            r"Use \[draft](report.txt) for details.",
            r"Use [draft\](report.txt) for details.",
            r"Use !\[chart\](chart.png) as the example.",
            r"Use !\[chart](chart.png) as the example.",
            r"Use ![chart\](chart.png) as the example.",
            r"The \[link\] is literal." + "\n\n[link]: /destination\n",
            r"The !\[chart\] is literal." + "\n\n[chart]: chart.png\n",
            r"\[draft\]\[ref\]" + "\n\n[ref]: report.txt\n",
            r"!\[chart\]\[ref\]" + "\n\n[ref]: chart.png\n",
            r"\[draft\]\[\]" + "\n\n[draft]: report.txt\n",
        ):
            with self.subTest(text=text):
                self.assert_round_trip(text)

    def test_literal_brackets_in_link_and_image_labels(self):
        for text in (
            r"[Use \] to close the array](/guide)",
            r"[Use \[ to open the array](/guide)",
            r"![Plot \] detail](chart.png)",
            r"![Plot \[ detail](chart.png)",
            r"[Use \] here][guide]" + "\n\n[guide]: /guide\n",
            r"![Plot \[ detail][chart]" + "\n\n[chart]: chart.png\n",
            r"[A *literal \]* in a label](/guide)",
            r"[![Plot \] detail](chart.png)](/guide)",
            "[Nested [brackets]](/guide)",
            "![Nested [brackets]](chart.png)",
        ):
            with self.subTest(text=text):
                self.assert_round_trip(text)

    def test_literal_brackets_in_text_tokens(self):
        for text, expected in (
            ("array[index]", r"array\[index\]"),
            ("unmatched [ bracket", r"unmatched \[ bracket"),
            ("unmatched ] bracket", r"unmatched \] bracket"),
            (r"Use \[draft\](report.txt).", r"Use \[draft\](report.txt)."),
            (r"[Use \] here](/guide)", r"[Use \] here](/guide)"),
            (r"![Plot \[ detail](chart.png)", r"![Plot \[ detail](chart.png)"),
        ):
            with self.subTest(text=text):
                output = self.reformat(text)
                self.assertEqual(output, expected + "\n")
                self.assertEqual(self.reformat(output), output)
                self.assert_round_trip(text)

        # Hooks may merge inline text tokens; brackets still need escaping.
        renderer = MarkdownRenderer()
        self.assertEqual(
            renderer.text({"type": "text", "raw": "Use [draft](report.txt)."}, BlockState()),
            r"Use \[draft\](report.txt).",
        )

    def test_literal_brackets_in_blocks_and_emphasis(self):
        for text in (
            r"# Use \[draft\](report.txt)",
            r"- Use \[draft\](report.txt)",
            r"> Use \[draft\](report.txt)",
            r"*Use \[draft\](report.txt)*",
            r"**Use \[draft\](report.txt)**",
            "First line\n" + r"\[draft\](report.txt)",
        ):
            with self.subTest(text=text):
                self.assert_round_trip(text)

    def test_literal_brackets_with_backslashes(self):
        for text in (
            r"[\\`a]`",
            r"[\*`a]`",
            r"\\\[draft\](report.txt)",
            r"Use \\ before \[draft\](report.txt).",
            r"[Use \\ before \] here](/guide)",
            r"![Use \\ before \[ here](chart.png)",
            r"[C:\documents\draft]",
        ):
            with self.subTest(text=text):
                self.assert_round_trip(text)
                output = self.reformat(text)
                self.assertEqual(self.reformat(output), output)

    def test_bracket_escaping_preserves_real_markup(self):
        for text in (
            "[draft](report.txt)",
            "![chart](chart.png)",
            "[draft][ref]\n\n[ref]: report.txt",
            "![chart][ref]\n\n[ref]: chart.png",
            "<https://example.com/path>",
            "<user@example.com>",
            "`[draft](report.txt)`",
            "```\n[draft](report.txt)\n```",
            '<span title="[draft]">example</span>',
            "<div>\n[draft](report.txt)\n</div>",
            '[draft](report.txt "[title]")',
        ):
            with self.subTest(text=text):
                self.assertEqual(self.reformat(text), text + "\n")
                self.assert_round_trip(text)

    def test_brackets_in_autolinks(self):
        for text in (
            "<https://example.com/[draft]>",
            "<https://example.com/draft]>",
            "<https://[::1]/>",
        ):
            with self.subTest(text=text):
                self.assert_round_trip(text)

    def test_escaped_emphasis_markers(self):
        # an escaped "*"/"_" is a literal delimiter, not emphasis; re-emitting
        # it unescaped would turn plain text back into <em>/<strong>
        for text in (
            r"\*not emphasis\*" + "\n",
            r"\_not emphasis\_" + "\n",
            r"\*\*not strong\*\*" + "\n",
            r"\_\_not strong\_\_" + "\n",
            r"a word\_with\_underscores" + "\n",
            r"2 \* 3 \* 4" + "\n",
            r"trailing star\*" + "\n",
            r"\*leading star" + "\n",
        ):
            self.assert_round_trip(text)

    def test_real_emphasis_not_over_escaped(self):
        # genuine emphasis must survive untouched, and prose punctuation with
        # spaces around a "*"/"_" must not gain stray backslashes
        for text in (
            "*emphasis*\n",
            "**strong**\n",
            "***both***\n",
            "_under_ and __strong__\n",
            "a *b* and _c_ mixed\n",
            "2 * 3 = 6 and 4 * 5\n",
            "snake_case_variable\n",
        ):
            self.assert_round_trip(text)

    def test_codespan_containing_backticks(self):
        # the delimiter must grow past any backtick run inside the code span,
        # and pad away a leading/trailing backtick, or the re-parse breaks
        for text in (
            "``a single ` backtick``\n",
            "``` two `` backticks ```\n",
            "`` `leading backtick``\n",
            "``trailing backtick` ``\n",
            "`` `surrounded` ``\n",
        ):
            self.assert_round_trip(text)

    def test_link_title_containing_quote(self):
        # a double quote inside a link/image title must be escaped, or the
        # re-parse closes the title early and drops it
        for text in (
            "[t](/u 'say \"hi\"')\n",
            '[t](/u "say \\"hi\\"")\n',
            "![a](/u 'say \"hi\"')\n",
            "[t][r]\n\n[r]: /u 'say \"hi\"'\n",
            '[t](/u "back\\\\slash \\" quote")\n',
        ):
            self.assert_round_trip(text)

    def test_block_quote_content_ending_in_gt(self):
        # a block quote whose content ends with ">" (an autolink, an inline
        # HTML tag, or a literal ">") must keep that character; it was being
        # stripped along with the trailing quote marker
        for text in (
            "> <https://example.com>\n",
            "> <b>raw</b>\n",
            "> ends with a literal &gt; >\n",
            "> > nested <https://example.com>\n",
            "> first\n>\n> <https://example.com>\n",
        ):
            self.assert_round_trip(text)

    def test_multiline_setext_heading(self):
        # a setext heading may span several lines; re-emitting it as an ATX
        # heading ("# ...") drops every line after the first out of the
        # heading, because an ATX heading is a single line
        for text in (
            "Foo\nBar\n===\n",
            "Foo\nBar\n---\n",
            "one\ntwo\nthree\n===\n",
            "Foo *bar\nbaz*\n====\n",
        ):
            self.assert_round_trip(text)

    def test_real_markers_preserved(self):
        for text in (
            "* bullet\n",
            "# heading\n",
            "1. ordered\n",
            "> quote\n",
            "`code`\n",
            "*emphasis*\n",
        ):
            self.assert_round_trip(text)

    def test_prose_not_over_escaped(self):
        for text in (
            "snake_case_var\n",
            "use - dashes - here\n",
            "C# and a.b.c and 1.5\n",
            "ratio a/b is fine\n",
        ):
            self.assert_round_trip(text)


class TestRendererMethodRegistration(TestCase):
    def test_registered_renderer_method(self):
        renderer = HTMLRenderer(escape=False)

        def render_wiki(renderer, key, title):
            return f'<a href="/wiki/{key}">{title}</a>'

        renderer.register("wiki", render_wiki)
        token = {"type": "wiki", "raw": "python", "attrs": {"title": "Python"}}

        self.assertEqual(
            renderer.render_token(token, BlockState()),
            '<a href="/wiki/python">Python</a>',
        )


class TestMarkdownRendererPlugins(TestCase):
    def test_task_list_item_can_be_overridden(self):
        class MyRenderer(MarkdownRenderer):
            def task_list_item(self, token, state):
                return "TASK\n"

        md = create_markdown(renderer=MyRenderer(), plugins=["task_lists"])
        self.assertEqual(md("- [x] a task"), "TASK\n")

    def test_task_list_item_default_markdown(self):
        md = create_markdown(renderer=MarkdownRenderer(), plugins=["task_lists"])
        self.assertEqual(md("- [x] a task"), "- [x] a task\n")

    def test_table_markdown(self):
        md = create_markdown(renderer=MarkdownRenderer(), plugins=["table"])
        result = md("| A | B |\n|---|---|\n| 1 | 2 |\n")
        self.assertEqual(result, "| A | B |\n| --- | --- |\n| 1 | 2 |\n")

    def test_literal_brackets_with_plugins(self):
        for plugins, text, expected in (
            (
                ["task_lists"],
                r"- [x] Use \[draft\](report.txt)",
                r"- [x] Use \[draft\](report.txt)" + "\n",
            ),
            (
                ["table"],
                "| [Heading] |\n| --- |\n| " + r"\[draft\](report.txt) |",
                r"| \[Heading\] |" + "\n| --- |\n| " + r"\[draft\](report.txt) |" + "\n",
            ),
            (
                ["url"],
                r"See https://example.com and \[draft\](report.txt)",
                r"See <https://example.com> and \[draft\](report.txt)" + "\n",
            ),
        ):
            with self.subTest(plugins=plugins, text=text):
                reformat = create_markdown(renderer=MarkdownRenderer(), plugins=plugins)
                to_html = create_markdown(escape=False, plugins=plugins)
                output = reformat(text)
                self.assertEqual(output, expected)
                self.assertEqual(to_html(output), to_html(text))
                self.assertEqual(reformat(output), output)

    def test_standalone_list_item(self):
        renderer = MarkdownRenderer()
        token = {
            "type": "list_item",
            "children": [
                {
                    "type": "paragraph",
                    "children": [{"type": "text", "raw": "x"}],
                }
            ],
        }
        self.assertEqual(renderer.render_token(token, BlockState()), "- x\n\n")
