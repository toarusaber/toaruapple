from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, tooltip, qconnect
from aqt.progress import ProgressManager
from anki.hooks import addHook
import time

# 引入 mecab 相关配置和功能
from .config import Config
from . import reading

mecab = reading.MecabController()
config = Config()

class SimpleProgressDialog(QDialog):
    def __init__(self, parent=None):
        super(SimpleProgressDialog, self).__init__(parent)
        self.setWindowTitle("Simple Progress Example")
        self.setMinimumWidth(300)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)

        self.button_add_tasks = QPushButton("Add Furigana")
        self.button_add_tasks.clicked.connect(self.addfurigana)
        self.button_layout.addWidget(self.button_add_tasks)

        self.button_del_tasks = QPushButton("Del Furigana")
        self.button_del_tasks.clicked.connect(self.delfurigana)
        self.button_layout.addWidget(self.button_del_tasks)

        self.thread = None
        self.worker = None

        self.finished.connect(self.cleanup)  # 窗口关闭时调用 cleanup 方法

    def cleanup(self):
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def addfurigana(self):
        self.start_task("add")

    def delfurigana(self):
        self.start_task("del")

    def start_task(self, task_type):
        # 先停止现有线程
        self.cleanup()

        self.thread = QThread()
        if task_type == "add":
            self.worker = Worker(self.process_items_add)
        else:
            self.worker = Worker(self.process_items_del)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def process_items_add(self):
        progress = ProgressManager(mw)
        ids = mw.col.find_cards("deck:Words")
        total_ids = len(ids)
        
        if total_ids == 0:
            mw.taskman.run_on_main(lambda: showInfo("No cards found in the 'Words' deck."))
            return
        
        col = mw.col
        mw.taskman.run_on_main(lambda: progress.start(label="Processing items...", max=total_ids))
        processed_count = 0

        def update_task(i):
            nonlocal processed_count
            processed_count += 1
            try:
                card = col.get_card(ids[i])
                noteid = card.nid
                note = col.get_note(noteid)
                srt = note["Sentence"]
                toaruapple = note["toaruapple"]

                if toaruapple == '' or toaruapple == 'arutoapple':
                    html = removeFurigana(srt)
                    html = mecab.reading(html, config.getIgnoreNumbers(), config.getUseRubyTags())
                    html = str(html)

                    if html == srt:
                        tooltip("Nothing to generate!")
                    else:
                        note["Sentence"] = html
                        col.update_note(note)
                        note["toaruapple"] = "toaruapple"
                        col.update_note(note)
                else:
                    return
                
                mw.taskman.run_on_main(lambda: progress.update(label=f"Processed {processed_count} / {total_ids}", value=processed_count))

            except Exception as e:
                mw.taskman.run_on_main(lambda: showInfo(f"Error retrieving card with ID {ids[i]}: {str(e)}"))

        for i in range(total_ids):
            QTimer.singleShot(1000 * i, lambda i=i: update_task(i))

        QTimer.singleShot(1000 * total_ids, lambda: self.finish_progress(progress, total_ids))

    def process_items_del(self):
        progress = ProgressManager(mw)
        ids = mw.col.find_cards("deck:Words")
        total_ids = len(ids)
        
        if total_ids == 0:
            mw.taskman.run_on_main(lambda: showInfo("No cards found in the 'Words' deck."))
            return
        
        col = mw.col
        mw.taskman.run_on_main(lambda: progress.start(label="Processing items...", max=total_ids))
        processed_count = 0

        def update_task(i):
            nonlocal processed_count
            processed_count += 1
            try:
                card = col.get_card(ids[i])
                noteid = card.nid
                note = col.get_note(noteid)
                srt = note["Sentence"]
                toaruapple = note["toaruapple"]

                if toaruapple == 'toaruapple':
                    html = removeFurigana(srt)
                    html = str(html)

                    if html == srt:
                        tooltip("No furigana found to delete")
                    else:
                        note["Sentence"] = html
                        col.update_note(note)
                        note["toaruapple"] = "arutoapple"
                        col.update_note(note)
                else:
                    return
                
                mw.taskman.run_on_main(lambda: progress.update(label=f"Processed {processed_count} / {total_ids}", value=processed_count))

            except Exception as e:
                mw.taskman.run_on_main(lambda: showInfo(f"Error retrieving card with ID {ids[i]}: {str(e)}"))

        for i in range(total_ids):
            QTimer.singleShot(1000 * i, lambda i=i: update_task(i))

        QTimer.singleShot(1000 * total_ids, lambda: self.finish_progress(progress, total_ids))

    def finish_progress(self, progress, total):
        mw.taskman.run_on_main(progress.finish)
        mw.taskman.run_on_main(lambda: showInfo(f"Processing completed. Total processed: {total}"))

class Worker(QObject):
    def __init__(self, func):
        super().__init__()
        self.func = func

    @pyqtSlot()
    def run(self):
        self.func()

def show_dialog():
    dialog = SimpleProgressDialog(mw)
    dialog.exec()

def setupMenu(browser):
    action = QAction("Run Simple Progress Example", browser)
    action.triggered.connect(show_dialog)
    browser.form.menuEdit.addAction(action)

addHook("browser.setupMenus", setupMenu)

# 引入 utils 模块中的 removeFurigana 函数
from .utils import removeFurigana

# 创建菜单项并绑定到函数
def testFunction() -> None:
    cardCount = mw.col.cardCount()
    showInfo("Card count: %d" % cardCount)

action = QAction("ToaruApple", mw)
qconnect(action.triggered, testFunction)
mw.form.menuTools.addAction(action)

def setupGuiMenu():
    useRubyTags = QAction("Use ruby tags", mw, checkable=True, checked=config.getUseRubyTags())
    useRubyTags.toggled.connect(config.setUseRubyTags)

    ignoreNumbers = QAction("Ignore numbers", mw, checkable=True, checked=config.getIgnoreNumbers())
    ignoreNumbers.toggled.connect(config.setIgnoreNumbers)

    mw.form.menuTools.addSeparator()
    mw.form.menuTools.addAction(useRubyTags)
    mw.form.menuTools.addAction(ignoreNumbers)

def toaru(browser):
    menu = browser.form.menuEdit
    menu.addSeparator()
    action = menu.addAction('ToaruFurigana')
    action.setShortcut(QKeySequence("Ctrl+Alt+Y"))
    qconnect(action.triggered, SimpleProgressDialog.addfurigana)

def aruto(browser):
    menu = browser.form.menuEdit
    menu.addSeparator()
    action = menu.addAction('ArutoFurigana')
    action.setShortcut(QKeySequence("Ctrl+Alt+U"))
    qconnect(action.triggered, SimpleProgressDialog.delfurigana)

setupGuiMenu()

addHook("browser.setupMenus", toaru)
addHook("browser.setupMenus", aruto)
