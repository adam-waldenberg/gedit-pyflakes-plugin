import ast
from gi.repository import Gedit
from gi.repository import GObject
from gi.repository import Pango
from operator import attrgetter
from pyflakes import checker
from pyflakes import messages


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
        try:
            for problem in self.check(document):
                line = problem.lineno - 1
                line_start = document.get_iter_at_line(line)
                line_end = document.get_iter_at_line(line)
                line_end.forward_to_line_end()
                keyword = None
                tag_start, tag_end = line_start, line_end
                if isinstance(problem, (messages.UnusedImport,
                                        messages.RedefinedWhileUnused,
                                        messages.ImportShadowedByLoopVar,
                                        messages.UndefinedName,
                                        messages.UndefinedExport,
                                        messages.UndefinedLocal,
                                        messages.DuplicateArgument,
                                        messages.Redefined,
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
                    if not tag_start or not tag_end:
                        tag_start, tag_end = line_start, line_end
                document.apply_tag(self.warn_tag, tag_start, tag_end)
        except SyntaxError as e:
            line = e.lineno - 1
            line_start = document.get_iter_at_line(line)
            line_end = document.get_iter_at_line(line)
            line_end.forward_to_line_end()
            document.apply_tag(self.err_tag, line_start, line_end)

    def check(self, document):
        filename = document.get_short_name_for_display()
        start, end = document.get_bounds()
        text = document.get_text(start, end, True)
        tree = ast.parse(text, filename)
        w = checker.Checker(tree, filename)
        w.messages.sort(key=attrgetter('lineno'))
        return w.messages
