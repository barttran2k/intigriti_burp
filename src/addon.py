from burp import IBurpExtender, ITab
from javax.swing import JTabbedPane
from Tabs import OptionsTab, ProgramsTab
from api import IntigritiApi, APIException
from helpers import BurpHTTP, async_call
import context


DEFAULT_URI = "https://api.intigriti.com/external/researcher/v1"
EXTENSION_NAME = "Intigriti Burp"
TAB_NAME = "Intigriti"
VERSION = "0.0.1"


class BurpExtender(IBurpExtender, ITab):
    connect_callback = list()
    error_callback = list()

    def registerExtenderCallbacks(self, callbacks):
        context.addon = self
        context.version = VERSION
        context.callbacks = callbacks
        context.callbacks.setExtensionName(EXTENSION_NAME)

        api_url = context.settings.load("apiurl", DEFAULT_URI)
        api_token = context.settings.load("api_token", "")

        context.api = IntigritiApi(api_url, fetcher=BurpHTTP(), token=api_token)

        context.tabs["Programs"] = ProgramsTab()
        context.tabs["Options"] = OptionsTab()
        tab = JTabbedPane(JTabbedPane.TOP)

        for name, panel in context.tabs.items():
            context.callbacks.customizeUiComponent(panel)
            tab.add(name, panel)

        self.getUiComponent = lambda: tab
        context.callbacks.addSuiteTab(self)
        if context.settings.load_bool("autoconnect", False):
            self.connect()

    def getTabCaption(self):
        return TAB_NAME

    def register_on_connect(self, callback):
        self.connect_callback.append(callback)

    def register_on_error(self, callback):
        self.error_callback.append(callback)

    def connect(self):
        def success(*args):
            for callback in self.connect_callback:
                callback()

        def error(error):
            for callback in self.error_callback:
                callback(error)

        async_call(context.api.authenticate, success, error)
