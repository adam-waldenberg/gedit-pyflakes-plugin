import ast
from gi.repository import GObject, Gedit, Pango
from operator import attrgetter
from pyflakes import checker, messages
import sys

class BlackHole(object):
    write = flush = lambda *args, **kwargs: None

    def __enter__(self):
        self.stderr, sys.stderr = sys.stderr, self

    def __exit__(self, *args, **kwargs):
        sys.stderr = self.stderr


class PyLocation(object):
    def __init__(self, lineno, col=None):
        self.lineno = lineno
        self.col_offset = col


class PySyntaxError(messages.Message):
    message = 'syntax error in line %d: %s'

    def __init__(self, filename, lineno, col, message):
        super(PySyntaxError, self).__init__(filename, lineno)
        self.message_args = (col, message)


class PyflakesPlugin(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = 'PyflakesPlugin'
    view = GObject.property(type=Gedit.View)
    document = GObject.property(type=Gedit.Document)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.document = self.view.get_buffer()
        self.err_tag = self.document.create_tag(None,
                                                underline_set=True,
                                                underline=Pango.Underline.ERROR)
        self.warn_tag = self.document.create_tag(None,
                                                 underline_set=True,
                                                 underline=Pango.Underline.ERROR,
                                                 foreground_set=True,
                                                 foreground='orange')
        self.handler = self.document.connect('highlight-updated', self.recheck)

    def do_deactivate(self):
        self.document.disconnect(self.handler)

    def recheck(self, document, *args):
        self.hide_errors(document)
        language = document.get_language()
        if language and language.get_name() == 'Python':
            self.show_errors(document)

    def hide_errors(self, document):
        bounds = document.get_bounds()
        self.document.remove_tag(self.err_tag, *bounds)
        self.document.remove_tag(self.warn_tag, *bounds)

    def show_errors(self, document):
        for problem in self.check(document):
            line = problem.lineno - 1
            line_start = document.get_iter_at_line(line)
            line_end = document.get_iter_at_line(line)
            line_end.forward_to_line_end()
            keyword = None
            tag_start = line_start
            tag_end = line_end
            if isinstance(problem, (messages.UnusedImport,
                                    messages.RedefinedWhileUnused,
                                    messages.ImportShadowedByLoopVar,
                                    messages.UndefinedName,
                                    messages.UndefinedExport,
                                    messages.UndefinedLocal,
                                    messages.DuplicateArgument,
                                    messages.RedefinedFunction,
                                    messages.LateFutureImport,
                                    messages.UnusedVariable)):
                keyword = problem.message_args[0]
            elif isinstance(problem, messages.ImportStarUsed):
                keyword = '*'
            if keyword:
                offset = line_start
                while offset.in_range(line_start, line_end):
                    tag_start, tag_end = offset.forward_search(keyword, 0,
                                                               line_end)
                    if tag_start.starts_word() and tag_end.ends_word():
                        break
                    offset.forward_word_end()

            tag_type = (self.err_tag if isinstance(problem, PySyntaxError)
                        else self.warn_tag)
            document.apply_tag(tag_type, tag_start, tag_end)

    def check(self, document):
        filename = document.get_short_name_for_display()
        start, end = document.get_bounds()
        text = document.get_text(start, end, True)
        try:
            with BlackHole():
                tree = ast.parse(text, filename)
        except SyntaxError, e:
            return [PySyntaxError(filename, e.lineno, e.offset, e.text)]
        else:
            w = checker.Checker(tree, filename)
            w.messages.sort(key=attrgetter('lineno'))
            return w.messages

