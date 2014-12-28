#!/usr/bin/env python
# encoding: utf-8
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, print_function

import os

from efl import ecore
from efl import elementary
from efl.evas import EVAS_HINT_EXPAND, EVAS_HINT_FILL
from efl.elementary.window import StandardWindow
from efl.elementary.innerwindow import InnerWindow
from efl.elementary.box import Box
from efl.elementary.ctxpopup import Ctxpopup
from efl.elementary.icon import Icon
from efl.elementary.label import Label
from efl.elementary.frame import Frame
from efl.elementary.genlist import Genlist, GenlistItemClass
from efl.elementary.button import Button
from efl.elementary.table import Table
from efl.elementary.check import Check
from efl.elementary.fileselector_button import FileselectorButton
from efl.elementary.fileselector import Fileselector
from efl.elementary.popup import Popup
from efl.elementary.progressbar import Progressbar
from efl.elementary.separator import Separator


EXPAND_BOTH = EVAS_HINT_EXPAND, EVAS_HINT_EXPAND
EXPAND_HORIZ = EVAS_HINT_EXPAND, 0.0
FILL_BOTH = EVAS_HINT_FILL, EVAS_HINT_FILL
FILL_HORIZ = EVAS_HINT_FILL, 0.0


def gl_text_get(obj, part, item_data):
    return item_data

def gl_fold_icon_get(obj, part, item_data):
    return Icon(obj, standard='folder')

def gl_file_icon_get(obj, part, item_data):
    return Icon(obj, standard='file')


class MainWin(StandardWindow):
    def __init__(self, fname, backend):
        self.backend = backend
        self.fname = fname
        self.dest_folder = os.path.dirname(fname)
        self.post_extract_action = 'close' # or 'fm' or 'term'

        # the window
        StandardWindow.__init__(self, 'epack.py', 'Epack')
        self.autodel_set(True)
        self.callback_delete_request_add(lambda o: elementary.exit())

        # main vertical box
        vbox = Box(self, size_hint_weight=EXPAND_BOTH)
        self.resize_object_add(vbox)
        vbox.show()

        ### header horiz box (inside a padding frame)
        frame = Frame(self, style='pad_medium',
                      size_hint_weight=EXPAND_HORIZ,
                      size_hint_align=FILL_HORIZ)
        vbox.pack_end(frame)
        frame.show()
        
        hbox = Box(self, horizontal=True, size_hint_weight=EXPAND_HORIZ,
                   size_hint_align=FILL_HORIZ)
        frame.content = hbox
        hbox.show()

        # spinner
        self.spinner = Progressbar(hbox, style="wheel", pulse_mode=True)
        self.spinner.pulse(True)
        self.spinner.show()
        hbox.pack_end(self.spinner)

        # info label
        self.hlabel = Label(hbox, text="Reading archive, please wait...",
                            size_hint_weight=EXPAND_HORIZ,
                            size_hint_align=(0.0, 0.5))
        self.hlabel.show()
        hbox.pack_end(self.hlabel)

        # genlist with archive content
        self.file_itc = GenlistItemClass(item_style="one_icon",
                                         text_get_func=gl_text_get,
                                         content_get_func=gl_file_icon_get)
        self.fold_itc = GenlistItemClass(item_style="one_icon",
                                         text_get_func=gl_text_get,
                                         content_get_func=gl_fold_icon_get)
        self.file_list = Genlist(self, homogeneous=True,
                                 size_hint_weight=EXPAND_BOTH,
                                 size_hint_align=FILL_BOTH)
        vbox.pack_end(self.file_list)
        self.file_list.show()

        ### footer table (inside a padding frame)
        frame = Frame(self, style='pad_medium',
                      size_hint_weight=EXPAND_HORIZ,
                      size_hint_align=FILL_HORIZ)
        vbox.pack_end(frame)
        frame.show()
        
        table = Table(frame)
        frame.content = table
        table.show()

        # FileSelectorButton
        self.fsb = DestinationButton(self)
        self.fsb.text = self.dest_folder
        self.fsb.callback_file_chosen_add(self.chosen_folder_cb)
        table.pack(self.fsb, 0, 0, 3, 1)
        self.fsb.show()

        sep = Separator(table, horizontal=True,
                        size_hint_weight=EXPAND_HORIZ)
        table.pack(sep, 0, 1, 3, 1)
        sep.show()

        # extract button
        btn_box = Box(table, horizontal=True)
        table.pack(btn_box, 0, 2, 1, 2)
        btn_box.show()
        
        self.btn1 = Button(table, text='Extract', disabled=True)
        self.btn1.callback_clicked_add(self.extract_btn_cb)
        btn_box.pack_end(self.btn1)
        self.btn1.show()

        ic = Icon(table, standard='arrow_up', size_hint_min=(17,17))
        self.btn2 = Button(table, content=ic)
        self.btn2.callback_clicked_add(self.extract_opts_cb)
        btn_box.pack_end(self.btn2)
        self.btn2.show()

        sep = Separator(table, horizontal=False)
        table.pack(sep, 1, 2, 1, 2)
        sep.show()

        # delete archive checkbox
        self.del_chk = Check(table, text="Delete archive after extraction",
                             size_hint_weight=EXPAND_HORIZ,
                             size_hint_align=(0.0, 1.0))
        table.pack(self.del_chk, 2, 2, 1, 1)
        self.del_chk.show()

        # create archive folder
        self.create_folder_chk = Check(table, text="Create archive folder",
                                       size_hint_weight=EXPAND_HORIZ,
                                       size_hint_align=(0.0, 1.0))
        table.pack(self.create_folder_chk, 2, 3, 1, 1)
        self.create_folder_chk.callback_changed_add(
                               lambda c: self.update_fsb_label())
        self.create_folder_chk.show()

        # ask for the archive content list
        self.backend.list_content(self.fname, self.list_done_cb)

        # show the window
        self.resize(300, 300)
        self.show()

    def extract_opts_cb(self, bt):
        ctx = Ctxpopup(self, hover_parent=self)
        ctx.item_append('Extract and open FileManager', None,
                        self.change_post_extract_action, 'fm')
        ctx.item_append('Extract and open in Terminal', None,
                        self.change_post_extract_action, 'term')
        ctx.item_append('Extract and close', None,
                        self.change_post_extract_action, 'close')
        x, y, w, h = bt.geometry
        ctx.pos = (x + w / 2, y)
        ctx.show()

    def change_post_extract_action(self, ctx, item, action):
        self.post_extract_action = action
        if action == 'fm':
            self.btn1.text = 'Extract and open FileManager'
        elif action == 'term':
            self.btn1.text = 'Extract and open in Terminal'
        elif action == 'close':
            self.btn1.text = 'Extract'
        ctx.delete()

    def update_header(self):
        self.hlabel.text = "<b>Archive:</b> %s" % (os.path.basename(self.fname))

    def update_fsb_label(self):
        if self.create_folder_chk.state is True:
            name = os.path.splitext(os.path.basename(self.fname))[0]
            self.fsb.text = os.path.join(self.dest_folder, name)
        else:
            self.fsb.text = self.dest_folder

    def show_error_msg(self, msg):
        pop = Popup(self, text=msg)
        pop.part_text_set('title,text', 'Error')

        btn = Button(self, text='Continue')
        btn.callback_clicked_add(lambda b: pop.delete())
        pop.part_content_set('button1', btn)

        btn = Button(self, text='Exit')
        btn.callback_clicked_add(lambda b: elementary.exit())
        pop.part_content_set('button2', btn)

        pop.show()

    def chosen_folder_cb(self, fsb, folder):
        if folder:
            self.dest_folder = folder
            self.update_fsb_label()

    def extract_btn_cb(self, btn):
        pp = Popup(self)
        pp.part_text_set('title,text', 'Extracting files, please wait...')
        pp.show()

        vbox = Box(self)
        pp.part_content_set('default', vbox)
        vbox.show()

        lb = Label(self, ellipsis=True, size_hint_weight=EXPAND_HORIZ,
                   size_hint_align=FILL_HORIZ)
        vbox.pack_end(lb)
        lb.show()

        pb = Progressbar(pp, size_hint_weight=EXPAND_HORIZ,
                         size_hint_align=FILL_HORIZ)
        vbox.pack_end(pb)
        pb.show()

        bt = Button(pp, text='Cancel', disabled=True)
        pp.part_content_set('button1', bt)

        self.prog_pbar = pb
        self.prog_label = lb
        self.popup = pp

        folder = self.fsb.text
        if not os.path.exists(folder):
            os.mkdir(folder)

        self.backend.extract(self.fname, folder,
                             self.extract_progress_cb,
                             self.extract_done_cb)

    def list_done_cb(self, file_list):
        for fname in file_list:
            if fname.endswith('/'):
                self.file_list.item_append(self.fold_itc, fname)
            else:
                self.file_list.item_append(self.file_itc, fname)

        self.spinner.pulse(False)
        self.spinner.delete()
        self.btn1.disabled = False
        self.update_header()

    def extract_progress_cb(self, progress, fname):
        self.prog_pbar.value = progress
        self.prog_label.text = fname

    def extract_done_cb(self, result):
        if result == 'success':
            if self.del_chk.state == True:
                os.remove(self.fname)
            elementary.exit()
        else:
            self.show_error_msg(result)
            self.popup.delete()


class ErrorWin(StandardWindow):
    def __init__(self, msg):
        StandardWindow.__init__(self, 'epack.py', 'Epack', autodel=True)
        self.callback_delete_request_add(lambda o: elementary.exit())

        inwin = InnerWindow(self, content=Label(self, text=msg))
        inwin.show()

        self.resize(300, 150)
        self.show()


class DestinationButton(FileselectorButton):
    def __init__(self, parent):
        FileselectorButton.__init__(self, parent,
                    inwin_mode=False, folder_only=True,
                    size_hint_weight=EXPAND_HORIZ, size_hint_align=FILL_HORIZ)
        self._text = ''

        box = Box(self, horizontal=True, padding=(3,0))
        self.content = box
        box.show()

        icon = Icon(box, standard='folder', size_hint_min=(16,16))
        box.pack_end(icon)
        icon.show()

        self.label = Label(box, ellipsis=True,
                           size_hint_weight=EXPAND_BOTH,
                           size_hint_align=FILL_HORIZ)
        box.pack_end(self.label)
        self.label.show()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        self._text = text
        self.label.text = '<align=left>%s</align>' % text


class FileChooserWin(StandardWindow):
    def __init__(self, backend):
        self.backend = backend
        StandardWindow.__init__(self, 'epack.py', 'Choose an archive')
        self.autodel_set(True)
        self.callback_delete_request_add(lambda o: elementary.exit())

        fs = Fileselector(self, expandable=False,
                          path=os.path.expanduser('~'),
                          size_hint_weight=EXPAND_BOTH,
                          size_hint_align=FILL_BOTH)
        fs.callback_done_add(self.done_cb)
        # TODO this filter seems not to work well...need fixing
        # fs.mime_types_filter_append(list(EXTRACT_MAP.keys()), 'Archive files')
        # fs.mime_types_filter_append(['*'], 'All files')
        fs.show()

        self.resize_object_add(fs)
        self.resize(300, 400)
        self.show()

    def done_cb(self, fs, path):
        if path is None:
            elementary.exit()
            return

        if not os.path.isdir(path):
            MainWin(path, self.backend)
            self.delete()

