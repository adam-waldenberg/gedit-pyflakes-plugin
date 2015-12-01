import ast
from gi.repository import Gedit
from gi.repository import GObject
from gi.repository import Gtk
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
        self.handlers = []
        self.problems = []
        self.warnings = PyflakesPlugin.find_msg_attr(PYFLAKES_MESSAGES_WARNING)
        GObject.Object.__init__(self)

    def do_activate(self):
        self.document = self.view.get_buffer()
        self.view.set_has_tooltip(True)
        self.err_tag = self.document.create_tag(None,
                                                underline_set=True,
                                                underline=Pango.Underline.ERROR)
        self.warn_tag = self.document.create_tag(None,
                                                 underline_set=True,
                                                 underline=Pango.Underline.ERROR,
                                                 foreground_set=True,
                                                 foreground='orange')
        self.handlers = [
            (self.document, self.document.connect('highlight-updated', self.do_recheck)),
            (self.view, self.view.connect('query-tooltip', self.do_query_tooltip))
        ]

    def do_deactivate(self):
        for i in self.handlers:
            i[0].disconnect(i[1])

    def do_recheck(self, document, *args):
        self.hide_errors(document)
        language = document.get_language()
        if language and language.get_name() == 'Python':
            self.show_errors(document)

    def do_query_tooltip(self, view, x, y, keyboard_mode, tooltip):
        start = None
        if keyboard_mode:
            cursor_position = self.document.get_property('cursor-position')
            start = self.document.get_iter_at_offset(cursor_position)
        else:
            try:
                width = view.get_gutter(Gtk.TextWindowType.LEFT).get_window().get_width()
            except AttributeError: # If there is no gutter...
                width = 0
            coords = view.window_to_buffer_coords(Gtk.TextWindowType.TEXT, x - width, y)
            start,_ = view.get_iter_at_position(*coords)
        return self.create_tooltip(tooltip, start)

    def create_tooltip(self, tooltip, start):
        try:
            is_on_tooltip_line = lambda x: x.lineno == start.get_line() + 1
            message = next(filter(is_on_tooltip_line, self.problems))
            if start.has_tag(self.err_tag):
                tooltip.set_markup("<b>" + str(message) + "</b>")
                return True
            elif start.has_tag(self.warn_tag):
                tooltip.set_markup(str(message))
                return True
        except StopIteration:
            pass
        return False


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
            self.problems = self.check(document)
            for problem in self.problems:
                start, end = PyflakesPlugin.get_line_interval(
                                                  document, problem.lineno - 1)
                start, end = self.find_keyword(problem, start, end)
                classes = tuple([i[0] for i in self.warnings])
                tag_type = self.warn_tag if isinstance(problem, classes) \
                                         else self.err_tag
                self.document.apply_tag(tag_type, start, end)
        except SyntaxError as e:
            self.problems = [e]
            start, end = PyflakesPlugin.get_line_interval(document, e.lineno - 1)
            self.document.apply_tag(self.err_tag, start, end)

    def check(self, document):
        filename = document.get_short_name_for_display()
        start, end = document.get_bounds()
        text = document.get_text(start, end, True)
        tree = ast.parse(text, filename)
        w = checker.Checker(tree, filename)
        w.messages.sort(key=attrgetter('lineno'))
        return w.messages
