#!/usr/bin/env python3
# coding: utf-8
"""
 .d8888b.  8888888 888b     d888 8888888b.       888b     d888 888
d88P  Y88b   888   8888b   d8888 888   Y88b      8888b   d8888 888
888    888   888   88888b.d88888 888    888      88888b.d88888 888
888          888   888Y88888P888 888   d88P      888Y88888P888 888
888  88888   888   888 Y888P 888 8888888P"       888 Y888P 888 888
888    888   888   888  Y8P  888 888             888  Y8P  888 888
Y88b  d88P   888   888   "   888 888             888   "   888 888
 "Y8888P88 8888888 888       888 888             888       888 88888888


Extracts the monocular depth of the current layer.
"""
import sys
import gi

gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import gettext
import subprocess
import pickle
import os

_ = gettext.gettext
image_paths = {"colorpalette": os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'colorpalette',
                                            'color_palette.png'),
               "logo": os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'images',
                                    'plugin_logo.png'),
               "error": os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'images',
                                     'error_icon.png')}


def N_(message): return message


def show_dialog(message, title, icon="logo"):
    use_header_bar = Gtk.Settings.get_default().get_property("gtk-dialogs-use-header")
    dialog = GimpUi.Dialog(use_header_bar=use_header_bar, title=_(title))
    # Add buttons
    dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("_OK", Gtk.ResponseType.APPLY)
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, homogeneous=False, spacing=10)
    dialog.get_content_area().add(vbox)
    vbox.show()

    # Create grid to set all the properties inside.
    grid = Gtk.Grid()
    grid.set_column_homogeneous(False)
    grid.set_border_width(10)
    grid.set_column_spacing(10)
    grid.set_row_spacing(10)
    vbox.add(grid)
    grid.show()

    # Show Logo
    logo = Gtk.Image.new_from_file(image_paths[icon])
    # vbox.pack_start(logo, False, False, 1)
    grid.attach(logo, 0, 0, 1, 1)
    logo.show()
    # Show message
    label = Gtk.Label(label=_(message))
    # vbox.pack_start(label, False, False, 1)
    grid.attach(label, 1, 0, 1, 1)
    label.show()
    dialog.show()
    dialog.run()
    return


def monodepth(procedure, image, drawable, force_cpu, progress_bar, config_path_output):
    # Save inference parameters and layers
    weight_path = config_path_output["weight_path"]
    python_path = config_path_output["python_path"]
    plugin_path = config_path_output["plugin_path"]

    Gimp.context_push()
    image.undo_group_start()

    interlace, compression = 0, 2
    Gimp.get_pdb().run_procedure('file-png-save', [
        GObject.Value(Gimp.RunMode, Gimp.RunMode.NONINTERACTIVE),
        GObject.Value(Gimp.Image, image),
        GObject.Value(GObject.TYPE_INT, 1),
        GObject.Value(Gimp.ObjectArray, Gimp.ObjectArray.new(Gimp.Drawable, drawable, 0)),
        GObject.Value(Gio.File, Gio.File.new_for_path(os.path.join(weight_path, '..', 'cache.png'))),
        GObject.Value(GObject.TYPE_BOOLEAN, interlace),
        GObject.Value(GObject.TYPE_INT, compression),
        # write all PNG chunks except oFFs(ets)
        GObject.Value(GObject.TYPE_BOOLEAN, True),
        GObject.Value(GObject.TYPE_BOOLEAN, True),
        GObject.Value(GObject.TYPE_BOOLEAN, False),
        GObject.Value(GObject.TYPE_BOOLEAN, True),
    ])

    with open(os.path.join(weight_path, '..', 'gimp_ml_run.pkl'), 'wb') as file:
        pickle.dump({"force_cpu": bool(force_cpu), "inference_status": "started"}, file)

    # Run inference and load as layer
    subprocess.call([python_path, plugin_path])
    with open(os.path.join(weight_path, '..', 'gimp_ml_run.pkl'), 'rb') as file:
        data_output = pickle.load(file)
    image.undo_group_end()
    Gimp.context_pop()
    if data_output["inference_status"] == "success":
        result = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,
                                Gio.file_new_for_path(os.path.join(weight_path, '..', 'cache.png')))
        result_layer = result.get_active_layer()
        copy = Gimp.Layer.new_from_drawable(result_layer, image)
        copy.set_name("Mono Depth")
        copy.set_mode(Gimp.LayerMode.NORMAL_LEGACY)  # DIFFERENCE_LEGACY
        image.insert_layer(copy, None, -1)



        # Remove temporary layers that were saved
        my_dir = os.path.join(weight_path, '..')
        for f_name in os.listdir(my_dir):
            if f_name.startswith("cache"):
                os.remove(os.path.join(my_dir, f_name))

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())
    else:
        show_dialog("Inference not successful. See error_log.txt in GIMP-ML folder.", "Error !", "error")
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


def run(procedure, run_mode, image, n_drawables, layer, args, data):
    # gio_file = args.index(0)
    # bucket_size = args.index(0)
    force_cpu = args.index(1)
    # output_format = args.index(2)

    progress_bar = None
    config = None

    if run_mode == Gimp.RunMode.INTERACTIVE:
        # Get all paths
        config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "tools")
        with open(os.path.join(config_path, 'gimp_ml_config.pkl'), 'rb') as file:
            config_path_output = pickle.load(file)
        python_path = config_path_output["python_path"]
        config_path_output["plugin_path"] = os.path.join(config_path, 'monodepth.py')

        config = procedure.create_config()
        config.set_property("force_cpu", force_cpu)
        config.begin_run(image, run_mode, args)

        GimpUi.init("monodepth.py")
        use_header_bar = Gtk.Settings.get_default().get_property("gtk-dialogs-use-header")

        # Create UI
        dialog = GimpUi.Dialog(use_header_bar=use_header_bar, title=_("Mono Depth..."))
        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("_Help", Gtk.ResponseType.APPLY)
        dialog.add_button("_Run Inference", Gtk.ResponseType.OK)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, homogeneous=False, spacing=10)
        dialog.get_content_area().add(vbox)
        vbox.show()

        # Create grid to set all the properties inside.
        grid = Gtk.Grid()
        grid.set_column_homogeneous(False)
        grid.set_border_width(10)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        vbox.add(grid)
        grid.show()

        # Show Logo
        logo = Gtk.Image.new_from_file(image_paths["logo"])
        # grid.attach(logo, 0, 0, 1, 1)
        vbox.pack_start(logo, False, False, 1)
        logo.show()

        # Show License
        license_text = _("PLUGIN LICENSE : MIT")
        label = Gtk.Label(label=license_text)
        # grid.attach(label, 1, 1, 1, 1)
        vbox.pack_start(label, False, False, 1)
        label.show()

        # Show ideal image size text
        label = Gtk.Label(label="384 X 384 px | ")
        grid.attach(label, 1, 0, 1, 1)
        # vbox.pack_start(label, False, False, 1)
        label.show()

        # Force CPU parameter
        spin = GimpUi.prop_check_button_new(config, "force_cpu", _("Force _CPU"))
        spin.set_tooltip_text(_("If checked, CPU is used for model inference."
                                " Otherwise, GPU will be used if available."))
        grid.attach(spin, 2, 0, 1, 1)
        spin.show()

        progress_bar = Gtk.ProgressBar()
        vbox.add(progress_bar)
        progress_bar.show()

        # Wait for user to click
        dialog.show()
        while True:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                force_cpu = config.get_property("force_cpu")
                result = monodepth(procedure, image, layer, force_cpu, progress_bar, config_path_output)
                # If the execution was successful, save parameters so they will be restored next time we show dialog.
                if result.index(0) == Gimp.PDBStatusType.SUCCESS and config is not None:
                    config.end_run(Gimp.PDBStatusType.SUCCESS)
                return result
            elif response == Gtk.ResponseType.APPLY:
                url = "https://github.com/kritiksoman/GIMP-ML/blob/GIMP3-ML/docs/MANUAL.md"
                Gio.app_info_launch_default_for_uri(url, None)
                continue
            else:
                dialog.destroy()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())


class MonoDepth(Gimp.PlugIn):
    ## Parameters ##
    __gproperties__ = {
        "force_cpu": (bool,
                      _("Force _CPU"),
                      "Force CPU",
                      False,
                      GObject.ParamFlags.READWRITE),
    }

    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        self.set_translation_domain("gimp30-python", Gio.file_new_for_path(Gimp.locale_directory()))
        return ['monodepth']

    def do_create_procedure(self, name):
        procedure = None
        if name == 'monodepth':
            procedure = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, run, None)
            procedure.set_image_types("*")
            procedure.set_documentation(
                N_("Extracts the monocular depth of the current layer."),
                globals()["__doc__"],  # This includes the docstring, on the top of the file
                name)
            procedure.set_menu_label(N_("_Mono Depth..."))
            procedure.set_attribution("Kritik Soman",
                                      "GIMP-ML",
                                      "2021")
            procedure.add_menu_path("<Image>/Layer/GIMP-ML/")
            procedure.add_argument_from_property(self, "force_cpu")

        return procedure


Gimp.main(MonoDepth.__gtype__, sys.argv)