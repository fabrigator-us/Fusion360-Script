"""
Fusion 360 Script: Export All Configurations as STL Files
----------------------------------------------------------
Uses the official ConfigurationTopTable API to iterate every row
(configuration) in the active design, activate it, and export the
root component as an STL to a folder you choose via dialog.

HOW TO USE:
  1. Open your Fusion 360 configured design file.
  2. Go to Tools > Add-Ins > Scripts and Add-Ins (Shift+S).
  3. Click the green "+" next to "My Scripts", point it at this file.
  4. Click "Run".
  5. Pick an output folder when the dialog appears.
  6. STLs are saved as  <RowName>.stl  in that folder.

API reference:
  https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Configurations_UM.htm
"""

import adsk.core
import adsk.fusion
import os
import traceback


def run(context):
    ui = None
    try:
        app: adsk.core.Application = adsk.core.Application.get()
        ui: adsk.core.UserInterface = app.userInterface
        design: adsk.fusion.Design = adsk.fusion.Design.cast(app.activeProduct)

        if not design:
            ui.messageBox("Please open a Fusion design first.")
            return

        # ── Check this is actually a configured design ────────────────────
        if not design.isConfiguredDesign:
            ui.messageBox(
                "This design has no configuration table.\n"
                "Exporting the active state as a single STL."
            )
            folder_dialog = ui.createFolderDialog()
            folder_dialog.title = "Select Output Folder for STL Files"
            if folder_dialog.showDialog() != adsk.core.DialogResults.DialogOK:
                return
            _export_stl(design, folder_dialog.folder,
                        _safe_filename(design.rootComponent.name or "export"))
            return

        # ── Choose output folder ──────────────────────────────────────────
        folder_dialog = ui.createFolderDialog()
        folder_dialog.title = "Select Output Folder for STL Files"
        if folder_dialog.showDialog() != adsk.core.DialogResults.DialogOK:
            ui.messageBox("Export cancelled.")
            return

        output_folder = folder_dialog.folder

        # ── Access the top configuration table ───────────────────────────
        # design.configurationTopTable  ->  ConfigurationTopTable
        # topTable.rows                 ->  ConfigurationRows collection
        # topTable.rows.count           ->  number of configurations
        # topTable.rows.item(i)         ->  ConfigurationRow
        # row.name                      ->  configuration name
        # row.activate()                ->  make this configuration active
        topTable: adsk.fusion.ConfigurationTopTable = design.configurationTopTable
        rows: adsk.fusion.ConfigurationRows = topTable.rows
        total = rows.count

        if total == 0:
            ui.messageBox("Configuration table exists but has no rows.")
            return

        exported = []
        failed = []

        for i in range(total):
            row: adsk.fusion.ConfigurationRow = rows.item(i)
            cfg_name = row.name
            safe_name = _safe_filename(cfg_name)

            try:
                row.activate()
                adsk.doEvents()  # let Fusion update the model

                _export_stl(design, output_folder, safe_name)
                exported.append(cfg_name)
            except Exception as e:
                failed.append(f"{cfg_name}: {e}")

        # ── Summary ───────────────────────────────────────────────────────
        lines = [
            "Export complete!",
            f"Folder: {output_folder}",
            "",
            f"Exported ({len(exported)}/{total}):",
        ]
        for name in exported:
            lines.append(f"  v  {name}")
        if failed:
            lines.append("")
            lines.append(f"Failed ({len(failed)}):")
            for f in failed:
                lines.append(f"  x  {f}")

        ui.messageBox("\n".join(lines))

    except Exception:
        if ui:
            ui.messageBox(f"Unexpected error:\n{traceback.format_exc()}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _export_stl(design: adsk.fusion.Design, output_folder: str, base_name: str):
    """Export the root component to <output_folder>/<base_name>.stl."""
    stl_path = os.path.join(output_folder, f"{base_name}.stl")

    export_mgr: adsk.fusion.ExportManager = design.exportManager
    stl_options: adsk.fusion.STLExportOptions = export_mgr.createSTLExportOptions(
        design.rootComponent, stl_path
    )

    # MediumMeshRefinement is a good balance of quality vs file size.
    # Change to HighMeshRefinement for finer meshes.
    stl_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium

    # Binary STL = smaller files. Set to False for ASCII.
    stl_options.isBinaryFormat = True

    # Don't open the print utility dialog after each export.
    stl_options.sendToPrintUtility = False

    export_mgr.execute(stl_options)


def _safe_filename(name: str) -> str:
    """Replace characters that are illegal in filenames."""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip() or "unnamed"