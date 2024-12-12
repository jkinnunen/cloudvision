import json
import sys
import os
import os.path
import time
from threading import Timer, Lock
from ..cvconf import getConfig, CONFIGDIR, bm_chat_id_file, bm_token_file
from ..cvexceptions import APIError

if sys.version_info.major == 2:
    import urllib as ur, urllib as up
elif sys.version_info.major == 3:
    import urllib.request as ur, urllib.parse as up

## for Windows XP
import socket

socket.setdefaulttimeout(60)

import wx
import ui
from logHandler import log
import queueHandler

class FocusedStaticText(wx.StaticText):
    def AcceptsFocus(self): return True

LOGGED_IN_TEXT = _("You are logged in to your account:")
class bm:
    url = "https://visionbot.ru/apiv2/"

    def __init__(self):
        self.lang = getConfig()["language"]
        if not os.path.isfile(bm_token_file):
            with open(bm_token_file, "w") as f:
                f.write(" ")
        if not os.path.isfile(bm_chat_id_file):
            with open(bm_chat_id_file, "w") as f:
                f.write("0")

    @property
    def bm_token(self):
        if not os.path.isfile(bm_token_file): return ""
        with open(bm_token_file) as f:
            return f.read(90).strip()

    @property
    def bm_chat_id(self):
        if not os.path.isfile(bm_chat_id_file): return 0
        with open(bm_chat_id_file) as f:
            return int(f.read(90).strip())

    @property
    def bm_authorized(self):
        return len(self.bm_token) > 20

    def refresh(self):
        params = {
            "action": "refresh",
            "bmtoken": self.bm_token
        }
        r1 = (
            ur.urlopen(self.url + "bm.php", data=up.urlencode(params).encode())
            .read()
            .decode("UTF-8")
        )
        j1 = json.loads(r1)
        if j1["status"] == "error":
            if "detail:" in j1["text"]: os.path.remove(bm_token_file)
            raise APIError(j1["text"])
        log.error(str(j1))
        return j1["text"]

    def ask(self, message, lang):
        is_chat_id_exists = False
        try:
            if int(self.bm_chat_id) != 0:
                is_chat_id_exists = True
        except ValueError:
            raise APIError("chat id not found. First, recognize the picture")
        params = {
            "action": "ask",
            "lang": lang,
            "bmtoken": self.bm_token,
            "bm_chat_id": self.bm_chat_id,
            "message": message,
        }
        r1 = (
            ur.urlopen(self.url + "bm.php", data=up.urlencode(params).encode())
            .read()
            .decode("UTF-8")
        )
        j1 = json.loads(r1)
        if j1["status"] == "error":
            raise APIError(j1["text"])
        params = {
            "id": j1["id"],
            "ask":"1",
        }
        for i in range(60):
            r2 = (
                ur.urlopen(
                    self.url + "res.php",
                    data=up.urlencode(params).encode(),
                )
                .read()
                .decode("UTF-8")
            )
            j2 = json.loads(r2)
            if j2["status"] == "error":
                raise APIError(j2.get("text", "unknown error"))

            if j2["status"] == "ok":
                return j2

            if j2["status"] == "notready":
                time.sleep(1)
                continue

    def login(self, email, password, lang="en"):
        params = {
            "action": "login",
            "lang": self.lang,
            "email": email,
            "password": password,
        }
        r = (
            ur.urlopen(self.url + "bm.php", data=up.urlencode(params).encode())
            .read()
            .decode("UTF-8")
        )
        j = json.loads(r)
        if j["status"] == "ok":
            with open(bm_token_file, "w") as f:
                f.write(j["bmtoken"])
        return j

    def signup(self, first_name, last_name, email, password, lang="en"):
        params = {
            "action": "signup",
            "lang": self.lang,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
        }
        r = (
            ur.urlopen(self.url + "bm.php", data=up.urlencode(params).encode())
            .read()
            .decode("UTF-8")
        )
        j = json.loads(r)
        if j["status"] == "ok":
            with open(bm_token_file, "w") as f:
                f.write(j["bmtoken"])
        return j


class LoginPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        email_sizer = wx.BoxSizer(wx.HORIZONTAL)
        email_label = wx.StaticText(self, label=_("Email:"))
        self.email_input = wx.TextCtrl(self)
        email_sizer.Add(email_label, 0, wx.ALL, 5)
        email_sizer.Add(self.email_input, 1, wx.EXPAND | wx.ALL, 5)

        password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        password_label = wx.StaticText(self, label=_("Password:"))
        self.password_input = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        password_sizer.Add(password_label, 0, wx.ALL, 5)
        password_sizer.Add(self.password_input, 1, wx.EXPAND | wx.ALL, 5)

        login_button = wx.Button(self, label=_("Log in"))
        login_button.Bind(wx.EVT_BUTTON, self.on_login)

        show_register_button = wx.Button(self, label=_("Create account"))
        show_register_button.Bind(wx.EVT_BUTTON, self.on_show_register_btn)

        main_sizer.Add(email_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(password_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(login_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        main_sizer.Add(show_register_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(main_sizer)

    def on_login(self, event):
        event.Skip()
        email = self.email_input.GetValue()
        password = self.password_input.GetValue()
        f = self.FindWindowByName("lrframe1")
        b = bm()
        res = b.login(email=email, password=password, lang=f.lang)
        wx.MessageBox(str(res))
        f.Close()

    def on_show_register_btn(self, event):
        event.Skip()
        self.Hide()
        f = self.FindWindowByName("lrframe1")
        f.register_panel.Show()
        f.Layout()
        f.register_panel.SetFocus()


class LoggedInPannel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.logged_in_h_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.logged_in_label = FocusedStaticText(self, wx.ID_ANY, LOGGED_IN_TEXT)
        self.logged_in_h_sizer.Add(self.logged_in_label, 0, 0, 0)

        self.logout_button = wx.Button(self, wx.ID_ANY, _("Logout"))
        self.logged_in_h_sizer.Add(self.logout_button, 0, 0, 0)

        self.SetSizer(self.logged_in_h_sizer)


        self.logout_button.Bind(wx.EVT_BUTTON, self.on_logout)
    def on_logout(self, event):
        event.Skip()
        with Lock():
            if os.path.isfile(bm_token_file): os.remove(bm_token_file)
        f = self.FindWindowByName("lrframe1")
        self.Hide()
        f.login_panel.Show()
        f.login_panel.email_input.SetFocus()

class RegisterPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(self, label=_("Name:"))
        self.name_input = wx.TextCtrl(self)
        name_sizer.Add(name_label, 0, wx.ALL, 5)
        name_sizer.Add(self.name_input, 1, wx.EXPAND | wx.ALL, 5)

        surname_sizer = wx.BoxSizer(wx.HORIZONTAL)
        surname_label = wx.StaticText(self, label=_("Surname:"))
        self.surname_input = wx.TextCtrl(self)
        surname_sizer.Add(surname_label, 0, wx.ALL, 5)
        surname_sizer.Add(self.surname_input, 1, wx.EXPAND | wx.ALL, 5)

        email_sizer = wx.BoxSizer(wx.HORIZONTAL)
        email_label = wx.StaticText(self, label=_("Email:"))
        self.email_input = wx.TextCtrl(self)
        email_sizer.Add(email_label, 0, wx.ALL, 5)
        email_sizer.Add(self.email_input, 1, wx.EXPAND | wx.ALL, 5)

        password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        password_label = wx.StaticText(self, label=_("Password:"))
        self.password_input = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        password_sizer.Add(password_label, 0, wx.ALL, 5)
        password_sizer.Add(self.password_input, 1, wx.EXPAND | wx.ALL, 5)

        register_button = wx.Button(self, label=_("Register"))
        register_button.Bind(wx.EVT_BUTTON, self.on_register)

        show_login_button = wx.Button(self, label=_("Log in"))
        show_login_button.Bind(wx.EVT_BUTTON, self.on_show_login_btn)

        main_sizer.Add(name_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(surname_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(email_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(password_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(register_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        main_sizer.Add(show_login_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.SetSizer(main_sizer)

    def on_show_login_btn(self, event):
        event.Skip()
        self.Hide()
        f = self.FindWindowByName("lrframe1")
        f.login_panel.Show()
        f.Layout()
        f.login_panel.SetFocus()

    def on_register(self, event):
        event.Skip()
        name = self.name_input.GetValue()
        surname = self.surname_input.GetValue()
        email = self.email_input.GetValue()
        password = self.password_input.GetValue()
        f = self.FindWindowByName("lrframe1")
        b = bm()
        res = b.signup(
            first_name=name,
            last_name=surname,
            email=email,
            password=password,
            lang=f.lang,
        )
        wx.MessageBox(str(res))
        f.Close()


class AskPanel(wx.Panel):
    ask_tmr = None

    def __init__(self, parent):
        super().__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        messages_sizer = wx.BoxSizer(wx.VERTICAL)
        self.messages_aria = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        messages_sizer.Add(self.messages_aria)

        question_sizer = wx.BoxSizer(wx.HORIZONTAL)
        question_label = wx.StaticText(self, label="Question:")
        self.question_input = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
        question_sizer.Add(question_label, 0, wx.ALL, 5)
        question_sizer.Add(self.question_input, 1, wx.EXPAND | wx.ALL, 5)

        send_close_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_button = wx.Button(self, label=_("Send"))
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)

        close_button = wx.Button(self, label=_("Close"))
        close_button.Bind(wx.EVT_BUTTON, self.on_close)
        send_close_sizer.Add(self.send_button)
        send_close_sizer.Add(close_button)

        main_sizer.Add(messages_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(question_sizer, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(send_close_sizer)

        self.SetSizer(main_sizer)

    def add_message(self, who, text, report=True):
        if report: queueHandler.queueFunction(queueHandler.eventQueue, ui.message, f"{who}: {text}")
        with Lock():
            text = self.messages_aria.GetValue() + "\n" + who + ": " + text
            self.messages_aria.SetValue(text)
        self.Layout()
    def on_send(self, event):
        event.Skip()
        if not bm().bm_authorized:
            self.messages_aria.SetFocus()
            return
        self.send_button.Disable()
        if self.ask_tmr and self.ask_tmr.is_alive():
            self.ask_tmr.cancel()
        self.ask_tmr = Timer(
            0.1,
            self._on_send,
            [
                event,
            ],
        )
        queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Wait for the Be My Eyes to type the message"))
        self.ask_tmr.start()

    def _on_send(self, event):
        message = self.question_input.GetValue()
        f = self.FindWindowByName("askframe1")
        try:
            b = bm()
            self.add_message(_("You"), message)
            self.question_input.SetValue("")
            res = b.ask(message=message, lang=f.lang)
        except APIError:
            wx.MessageBox(str(sys.exc_info()[1]), style=wx.ICON_ERROR)
            return False
        finally:
            self.send_button.Enable()
        self.add_message("Be My Eyes", res["text"])
        self.messages_aria.SetFocus()

    def on_close(self, event):
        f = self.FindWindowByName("askframe1")
        f.Hide()


class MainDialog(wx.Dialog):
    def __init__(self, parent=None, lang="en"):
        super().__init__(parent=parent, title="Manage Be My Eyes Account")

        self.lang = lang

        self.SetName("lrframe1")

        self.login_panel = LoginPanel(self)
        self.register_panel = RegisterPanel(self)
        self.logged_panel = LoggedInPannel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.login_panel, 1, wx.EXPAND)
        sizer.Add(self.logged_panel, 1, wx.EXPAND)
        sizer.Add(self.register_panel, 1, wx.EXPAND)

        for o in (self, self.login_panel, self.logged_panel, self.register_panel):
            o.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        bmtoken = ""
        if os.path.isfile(bm_token_file):
            with open(bm_token_file, "r") as f:
                bmtoken = f.read(90).strip()
        self.register_panel.Hide()
        if bm().bm_authorized:
            self.login_panel.Hide()
            refresh_result=""
            try:
                refresh_result = bm().refresh()
            except Exception:
                log.exception("Error get BM Account data")
                refresh_result = "..."
            self.logged_panel.logged_in_label.SetLabel(LOGGED_IN_TEXT+refresh_result)
            self.logged_panel.logged_in_label.SetFocus()
        else:
            self.logged_panel.Hide()
        self.SetSizer(sizer)
        self.Layout()
    def OnKeyUp(self, e):
        key = e.GetKeyCode()
        e.Skip()
        if key == 27:
            self.Close()


class AskFrame(wx.Frame):
    def __init__(self, parent=None, lang="en"):
        super().__init__(parent=None)
        self.lang = getConfig()["language"]
        self.SetTitle("Ask a question")

        self.SetName("askframe1")

        self.ask_panel = AskPanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ask_panel, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Layout()
        self.Bind(wx.EVT_CLOSE, self.on_close)
        if not bm().bm_authorized:
            _t = "\n".join([
                _("First you need to log in or register"),
                _("Open NVDA Menu, Preferences, CloudVision Settings, Manage Be My Eyes account")
            ])
            self.ask_panel.messages_aria.SetValue(_t)
            queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _t)

    def postInit(self):
        self.Layout()
        field = self.ask_panel.question_input if bm().bm_authorized else self.ask_panel.messages_aria
        field.SetFocus()

    def on_close(self, event):
        self.Hide()


if __name__ == "__main__":
    app = wx.App()
    dialog = MainDialog()
    dialog.ShowModal()
    app.MainLoop()
