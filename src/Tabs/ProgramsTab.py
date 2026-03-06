import context
from javax.swing import (
    JPanel,
    JList,
    JScrollPane,
    JSplitPane,
    DefaultListModel,
    ListSelectionModel,
    JLabel,
    BoxLayout,
    Box,
    JTable,
    JButton,
    JTextArea,
    ListCellRenderer
)
from javax.swing.border import EmptyBorder
from javax.swing.table import DefaultTableModel
from java.awt import BorderLayout, Dimension, Font, Color, FlowLayout
from BetterJava import ColumnPanel, make_title_border, SplitPanel, HTMLRenderer, CallbackActionListener
from helpers import async_call
from target_scope import TargetScopeImporter

class ProgramRenderer(ListCellRenderer, JLabel):
    def getListCellRendererComponent(self, jlist, program, index, isSelected, cellHashFocus):
        if isSelected:
            self.setBackground(Color(0x3B82F6)) # Blue
            self.setForeground(Color.white)
        else:
            self.setBackground(Color.white)
            self.setForeground(Color.black)
        
        self.setText(program.title)
        self.setOpaque(True)
        self.setBorder(EmptyBorder(5, 10, 5, 10))
        return self

class ScopeBox(JPanel):
    def __init__(self, scopes, on_import_all=None, on_import_selected=None):
        self.scopes = scopes or []
        self.on_import_all = on_import_all
        self.on_import_selected = on_import_selected
        self.setLayout(BorderLayout())
        self.setBorder(make_title_border("Scope Details"))
        
        # Columns: Type, Endpoint, Tier
        col_names = ["Type", "Endpoint", "Tier"]
        model = DefaultTableModel(col_names, 0)
        
        for s in self.scopes:
            model.addRow([s.type, s.endpoint, s.tier])
            
        self.table = JTable(model)
        self.table.setSelectionMode(ListSelectionModel.MULTIPLE_INTERVAL_SELECTION)
        self.table.setAutoCreateRowSorter(True)
        
        scroll_table = JScrollPane(self.table)
        scroll_table.setPreferredSize(Dimension(400, 200))
        
        self.desc_area = JTextArea()
        self.desc_area.setLineWrap(True)
        self.desc_area.setWrapStyleWord(True)
        self.desc_area.setEditable(False)
        scroll_desc = JScrollPane(self.desc_area)
        scroll_desc.setPreferredSize(Dimension(400, 100))
        scroll_desc.setBorder(make_title_border("Scope Description"))
        
        class SelectionListener:
            def valueChanged(self, event):
                if not event.getValueIsAdjusting():
                    row = self.table.getSelectedRow()
                    if row >= 0 and row < self.table.getRowCount():
                        # Map view index back to model index due to sorting
                        model_idx = self.table.convertRowIndexToModel(row)
                        self.desc_area.setText(self.scopes[model_idx].description)
        
        listener = SelectionListener()
        listener.table = self.table
        listener.desc_area = self.desc_area
        listener.scopes = self.scopes
        from javax.swing.event import ListSelectionListener
        class LSListener(ListSelectionListener):
            def __init__(self, l):
                self.l = l
            def valueChanged(self, e):
                self.l.valueChanged(e)

        self.table.getSelectionModel().addListSelectionListener(LSListener(listener))

        button_panel = JPanel(FlowLayout(FlowLayout.LEFT))
        self.import_all_btn = JButton("Import All to Burp Target")
        self.import_all_btn.addActionListener(CallbackActionListener(self._import_all))
        self.import_selected_btn = JButton("Import Selected to Burp Target")
        self.import_selected_btn.addActionListener(CallbackActionListener(self._import_selected))
        button_panel.add(self.import_all_btn)
        button_panel.add(self.import_selected_btn)

        self.status_label = JLabel("Ready")
        self.status_label.setOpaque(True)
        self._set_status("Ready", Color(0xF2F4F7), Color(0x1F2937))
        button_panel.add(self.status_label)
        
        split = SplitPanel(scroll_table, scroll_desc)
        split.setOrientation(JSplitPane.VERTICAL_SPLIT)
        # Increase default height allocation for Scope table
        split.setDividerLocation(350)
        
        self.add(split, BorderLayout.CENTER)
        self.add(button_panel, BorderLayout.SOUTH)

    def _set_status(self, message, bg=Color.WHITE, fg=Color.BLACK):
        self.status_label.setText(message)
        self.status_label.setBackground(bg)
        self.status_label.setForeground(fg)

    def _preview_skipped(self, skipped):
        if not skipped:
            return ""
        preview = skipped[:2]
        return "; ".join(
            "{} ({})".format(item.get("endpoint") or "<empty>", item.get("reason"))
            for item in preview
        )

    def _handle_import_result(self, result):
        if not result:
            self._set_status("Import failed: no result", Color(0xB80000), Color.WHITE)
            return

        if not result.get("ok"):
            message = result.get("message", "Import failed")
            self._set_status(message, Color(0xB80000), Color.WHITE)
            return

        message = result.get("message", "Import completed")
        skipped_preview = self._preview_skipped(result.get("skipped_details", []))
        if skipped_preview:
            message = "{} | {}".format(message, skipped_preview)

        if result.get("added", 0) > 0:
            self._set_status(message, Color(0x006400), Color.WHITE)
        elif result.get("duplicates", 0) > 0 or result.get("skipped", 0) > 0:
            self._set_status(message, Color(0xA16207), Color.WHITE)
        else:
            self._set_status(message, Color(0x1D4ED8), Color.WHITE)

    def get_selected_scopes(self):
        selected_rows = self.table.getSelectedRows()
        scopes = []
        for row in selected_rows:
            model_idx = self.table.convertRowIndexToModel(row)
            if model_idx >= 0 and model_idx < len(self.scopes):
                scopes.append(self.scopes[model_idx])
        return scopes

    def _import_all(self, event):
        if self.on_import_all is None:
            self._set_status("Import handler is not configured", Color(0xB80000), Color.WHITE)
            return
        try:
            result = self.on_import_all(self.scopes)
        except Exception as e:
            self._set_status("Import failed: {}".format(e), Color(0xB80000), Color.WHITE)
            return
        self._handle_import_result(result)

    def _import_selected(self, event):
        if self.on_import_selected is None:
            self._set_status("Import handler is not configured", Color(0xB80000), Color.WHITE)
            return
        selected_scopes = self.get_selected_scopes()
        if not selected_scopes:
            self._set_status("No scope selected", Color(0xA16207), Color.WHITE)
            return
        try:
            result = self.on_import_selected(selected_scopes)
        except Exception as e:
            self._set_status("Import failed: {}".format(e), Color(0xB80000), Color.WHITE)
            return
        self._handle_import_result(result)

import re

def parse_markdown(text):
    if not text:
        return ""
    # Convert newlines
    text = text.replace('\r\n', '\n')
    text = text.replace('\n', '<br>')
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Headers
    text = re.sub(r'#{3}\s*(.*?)(?:<br>|$)', r'<h3>\1</h3>', text)
    text = re.sub(r'#{2}\s*(.*?)(?:<br>|$)', r'<h2>\1</h2>', text)
    text = re.sub(r'#\s*(.*?)(?:<br>|$)', r'<h1>\1</h1>', text)
    # Lists (basic dash handling)
    text = re.sub(r'(?:<br>|^)-\s+(.*?)(?=(?:<br>|$))', r'<li>\1</li>', text)
    return text

class TitleBox(JPanel):
    def __init__(self, program):
        self.setLayout(BorderLayout())
        
        # Split title and attributes into North / South instead of West / East
        title = JLabel(program.title)
        title.setFont(Font("Arial", Font.BOLD, 22))
        title.setBorder(EmptyBorder(10, 5, 5, 5))
        
        attributes_panel = JPanel(FlowLayout(FlowLayout.LEFT, 15, 0))
        attributes_panel.setBorder(EmptyBorder(0, 5, 10, 5))
        
        def add_attribute(label_text, value_text):
            panel = JPanel(FlowLayout(FlowLayout.LEFT, 2, 0))
            lbl = JLabel(label_text)
            lbl.setFont(Font("Arial", Font.BOLD, 12))
            val = JLabel(value_text)
            val.setFont(Font("Arial", Font.PLAIN, 12))
            panel.add(lbl)
            panel.add(val)
            attributes_panel.add(panel)
        
        add_attribute("Status:", program.status)
        add_attribute("Type:", program.type)
        add_attribute("Industry:", program.industry if program.industry else "N/A")
        
        bounty_val = "{} - {}".format(program.min_bounty, program.max_bounty) if program.min_bounty != "N/A" else "N/A"
        add_attribute("Bounty:", bounty_val)

        self.add(title, BorderLayout.NORTH)
        self.add(attributes_panel, BorderLayout.SOUTH)
        self.setMaximumSize(Dimension(99999, self.getPreferredSize().height))

class RulesBox(JScrollPane):
    def __init__(self, raw_rules):
        parsed_html = parse_markdown(raw_rules or "")
        html = u"<html><body>{}</body></html>".format(parsed_html)
        html_renderer = HTMLRenderer(html)
        html_renderer.add_css_file("style.css")
        JScrollPane.__init__(self, html_renderer)
        self.putClientProperty("html.disable", None)
        self.setBorder(make_title_border("Rules of Engagement"))


class ProgramPane(JPanel):
    def __init__(self, program, on_import_all=None, on_import_selected=None):
        self.setLayout(BorderLayout())
        self.add(TitleBox(program), BorderLayout.NORTH)
        
        split = SplitPanel(
            RulesBox(program.rules_html),
            ScopeBox(
                program.scopes,
                on_import_all=on_import_all,
                on_import_selected=on_import_selected,
            ),
        )
        split.setDividerLocation(400)
        self.add(split, BorderLayout.CENTER)


class ProgramsTab(JPanel):
    def __init__(self):
        self.programs = []
        self.displayed_programs = []
        self.current_program_details = None
        self.scope_importer = TargetScopeImporter(context.callbacks)
        self.setLayout(BorderLayout())

        # Top panel with Refresh button and Search Bar
        top_panel = JPanel(FlowLayout(FlowLayout.LEFT))
        refresh_btn = JButton("Refresh Programs")
        refresh_btn.addActionListener(CallbackActionListener(self.refresh_programs))
        top_panel.add(refresh_btn)
        
        top_panel.add(JLabel(" Search: "))
        from javax.swing import JTextField
        self.search_field = JTextField(20)
        
        # Add search key listener
        from java.awt.event import KeyAdapter
        class SearchKeyListener(KeyAdapter):
            def __init__(self, parent):
                self.parent = parent
            def keyReleased(self, event):
                self.parent.filter_programs()
        self.search_field.addKeyListener(SearchKeyListener(self))
        top_panel.add(self.search_field)

        self.JprogramList = JList()
        self.JprogramList.setSelectionMode(ListSelectionModel.SINGLE_SELECTION)
        
        class SelectionListener:
            def __init__(self, parent):
                self.parent = parent
            def valueChanged(self, event):
                self.parent.handle_select(event)
                
        from javax.swing.event import ListSelectionListener
        class LSListener(ListSelectionListener):
            def __init__(self, l):
                self.l = l
            def valueChanged(self, e):
                self.l.valueChanged(e)
                
        self.JprogramList.addListSelectionListener(LSListener(SelectionListener(self)))
        
        scrollPane = JScrollPane(self.JprogramList)
        scrollPane.setMinimumSize(Dimension(250, 0))

        self.splitPane = SplitPanel(scrollPane, JPanel())
        
        # Combine everything
        self.add(top_panel, BorderLayout.NORTH)
        self.add(self.splitPane, BorderLayout.CENTER)
        
        context.addon.register_on_connect(self.load_program_list)
        context.addon.register_on_error(self.display_error)

    def refresh_programs(self, event):
        self.splitPane.setRightComponent(JLabel("Refreshing..."))
        self.load_program_list()

    def filter_programs(self):
        query = self.search_field.getText().lower()
        self.displayed_programs = [p for p in self.programs if query in p.title.lower()]
        
        model = DefaultListModel()
        for program in self.displayed_programs:
            model.addElement(program)
            
        self.JprogramList.setModel(model)
        if self.displayed_programs:
            self.JprogramList.setSelectedIndex(0)

    def load_program_list(self):
        async_call(context.api.get_programs, self.display_program_list, self.display_error)

    def display_program_list(self, programs):
        # Sort programs alphabetically by title
        self.programs = sorted(programs, key=lambda x: x.title.lower())
        
        # Initial filter applies to populate displayed_programs
        self.filter_programs()
        self.JprogramList.setCellRenderer(ProgramRenderer())

        if self.displayed_programs:
            first_program = self.displayed_programs[0]
            async_call(
                lambda: context.api.get_program_details(
                    first_program.id, first_program.raw
                ),
                self.load_program_details,
                self.display_error
            )
        else:
            self.splitPane.setRightComponent(JPanel())

    def display_error(self, error):
        self.current_program_details = None
        self.JprogramList.setListData(tuple())
        self.splitPane.setRightComponent(JLabel("Error or disconnected: {}".format(error)))

    def import_scopes_to_target(self, scopes):
        return self.scope_importer.import_scopes(scopes)

    def load_program_details(self, pgm_details):
        self.current_program_details = pgm_details
        pane = ProgramPane(
            pgm_details,
            on_import_all=self.import_scopes_to_target,
            on_import_selected=self.import_scopes_to_target,
        )
        loc = self.splitPane.getDividerLocation()
        self.splitPane.setRightComponent(pane)
        self.splitPane.setDividerLocation(loc)

    def handle_select(self, event):
        jlist = event.getSource()
        if event.getValueIsAdjusting():
            return None
        selected_idx = jlist.getSelectedIndex()
        if selected_idx < 0 or selected_idx >= len(self.displayed_programs):
            return None

        # Show Loading Indicator
        loading_label = JLabel("Loading Program Details...")
        loading_label.setFont(Font("Arial", Font.BOLD, 18))
        loading_label.setBorder(EmptyBorder(20, 20, 20, 20))
        self.splitPane.setRightComponent(loading_label)

        selected_program = self.displayed_programs[selected_idx]
        async_call(
            lambda: context.api.get_program_details(
                selected_program.id, selected_program.raw
            ),
            self.load_program_details,
            self.display_error
        )
