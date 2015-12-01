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

    @staticmethod
    def find_msg_attr(attributes):
        located_attributes = []
        for i in attributes:
            try:
                attr = (i[0], i[1]) if isinstance(i, tuple) else (i, None)
                located_attributes.append((getattr(messages, attr[0]), attr[1]))
            except AttributeError:
                pass
        return located_attributes

    def __init__(self):
        PYFLAKES_MESSAGES_WARNING = ['AssertTuple', ('ImportStarUsage', '*'),
                                     ('ImportStarUsed', '*'), 'UnusedImport',
                                     'UnusedVariable']
        self.warnings = PyflakesPlugin.find_msg_attr(PYFLAKES_MESSAGES_WARNING)
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
        self.handler = self.document.connect('highlight-updated', self.do_recheck)

    def do_deactivate(self):
        self.document.disconnect(self.handler)

    def do_recheck(self, document, *args):
        self.hide_errors(document)
        language = document.get_language()
        if language and language.get_name() == 'Python':
            self.show_errors(document)

    def hide_errors(self, document):
        bounds = document.get_bounds()
        self.document.remove_tag(self.err_tag, *bounds)
        self.document.remove_tag(self.warn_tag, *bounds)

    @staticmethod
    def get_line_interval(document, line):
        start = document.get_iter_at_line(line)
        end = document.get_iter_at_line(line)
        start.forward_to_line_end()
        start.backward_sentence_start()
        end.forward_to_line_end()
        return start, end

    def find_keyword(self, problem, start, end):
       tag_start, tag_end = start, end
       keyword = [i[1] for i in self.warnings if i[1] != None and
                                                 isinstance(problem, i[0])]
       keyword = (keyword or problem.message_args)[0]
       while start.in_range(start, end):
           tag_start, tag_end = start.forward_search(keyword, 0, end)
           if tag_start.starts_word() and tag_end.ends_word():
               break
           start.forward_word_end()
       if not tag_start or not tag_end:
           return start, end
       return tag_start, tag_end

    def show_errors(self, document):
        try:
            for problem in self.check(document):
                start, end = PyflakesPlugin.get_line_interval(
                                                  document, problem.lineno - 1)
                start, end = self.find_keyword(problem, start, end)
                classes = tuple([i[0] for i in self.warnings])
                tag_type = self.warn_tag if isinstance(problem, classes) \
                                         else self.err_tag
                document.apply_tag(tag_type, start, end)
        except SyntaxError as e:
            start, end = PyflakesPlugin.get_line_interval(
                                                  document, e.lineno - 1)
            document.apply_tag(self.err_tag, start, end)

    def check(self, document):
        filename = document.get_short_name_for_display()
        start, end = document.get_bounds()
        text = document.get_text(start, end, True)
        tree = ast.parse(text, filename)
        w = checker.Checker(tree, filename)
        w.messages.sort(key=attrgetter('lineno'))
        return w.messages
