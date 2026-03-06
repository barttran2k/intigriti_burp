import context
from java.lang import String
from javax.swing import (
    JPanel,
    JLabel,
    JPasswordField,
    JButton,
    JScrollPane,
)
from java.awt import Color, GridBagLayout, GridBagConstraints, Insets
from BetterJava import (
    ColumnPanel,
    make_title_border,
    make_constraints,
    CallbackActionListener,
)

def padding(size):
    return Insets(size, size, size, size)

class StatusText(JLabel):
    def __init__(self, *args, **kwargs):
        JLabel.__init__(self, *args, **kwargs)
        self.setOpaque(True)
        self.setHorizontalAlignment(JLabel.CENTER)

    def set(self, text, bg=Color.WHITE, fg=Color.BLACK):
        self.setText(text)
        self.setBackground(bg)
        self.setForeground(fg)

class APIBox(JPanel):
    def __init__(self):
        self.setLayout(GridBagLayout())
        self.setBorder(make_title_border("API Configuration"))
        self.setAlignmentX(JPanel.LEFT_ALIGNMENT)

        # Status Bar
        self.status = StatusText("Not Tested Yet")
        self.status.set("Not Tested Yet", Color.LIGHT_GRAY, Color.BLACK)
        self.add(JLabel("Status :"), gridx=0)
        self.add(self.status, gridx=1, anchor=GridBagConstraints.WEST, insets=padding(5), fill=GridBagConstraints.HORIZONTAL)

        # Token Input
        saved_token = context.settings.load("api_token", "")
        self.api_token_input = JPasswordField(25)
        self.api_token_input.setText(saved_token)
        self.add(JLabel("API Token :"), gridx=0)
        self.add(self.api_token_input, gridx=1, anchor=GridBagConstraints.WEST, insets=padding(5))

        # Buttons
        btn_group = JPanel()
        btn_save = JButton("Save")
        btn_save.addActionListener(CallbackActionListener(self.save_settings))
        btn_connect = JButton("Test Connection")
        btn_connect.addActionListener(CallbackActionListener(self.test_connection))

        btn_group.add(btn_save)
        btn_group.add(btn_connect)
        self.add(btn_group, gridx=1, anchor=GridBagConstraints.EAST, insets=padding(5))

        self.setMaximumSize(self.getPreferredSize())

    def save_settings(self, event):
        token = String(self.api_token_input.getPassword()).trim()
        context.settings.save("api_token", token)
        context.api.change_token(token)
        self.status.set("Settings Saved, fetching programs...", Color.LIGHT_GRAY, Color.BLACK)
        self.test_connection(event)

    def test_connection(self, event):
        self.status.set("Testing...", Color.GRAY, Color.WHITE)
        token = String(self.api_token_input.getPassword()).trim()
        context.settings.save("api_token", token)
        context.api.change_token(token)

        def success(*args):
            self.status.set("Connected Successfully!", Color(0x006400), Color.WHITE)
            context.addon.connect()
            
        def error(err):
            self.status.set("Error: {}".format(err), Color(0xB80000), Color.WHITE)

        from helpers import async_call
        async_call(context.api.authenticate, success, error)

    def add(self, el, **constraints):
        default = {"insets": padding(5), "anchor": GridBagConstraints.WEST}
        default.update(constraints)
        JPanel.add(self, el, make_constraints(**default))


class OptionsTab(JScrollPane):
    def __init__(self):
        panel = ColumnPanel()
        apibox = APIBox()
        panel.add(apibox)
        JScrollPane.__init__(self, panel)
