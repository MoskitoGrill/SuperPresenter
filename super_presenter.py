"""Compatible launcher and historical imports for SuperPresenter."""
from superpresenter.app import main
from superpresenter.ui.main_window import GUI, doNothing
from superpresenter.ui.projector_window import ProjWindow
from superpresenter.ui.projector_widgets import (
    Widget_OneLine, Widget_FlowLines, Widget_StanzaPaged, Widget_Image,
)
from superpresenter.ui.source_sorter import SortingWin
from superpresenter.services.presentation_session import (
    WidgetSource, _LegacyWidgetSource, readTagName, readFileName,
    clearEmpties, readTagParams, readTag,
)
# Historical integrations patch these shared tkinter modules.
import tkinter as tk
from tkinter import messagebox as tkmsg


if __name__ == '__main__':
    main()
