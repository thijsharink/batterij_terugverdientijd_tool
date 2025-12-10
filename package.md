# How to Package Your Application

This guide explains how to package your Python application into a single executable file using PyInstaller. This process will protect your source code and assets while allowing users to run it easily.

## Important: Building for Windows vs. macOS

An executable built on one operating system cannot run on another.
- To create a **Windows executable (`.exe`)**, you must run the PyInstaller command on a Windows machine.
- To create a **macOS executable**, you must run the command on a macOS machine.

## Step 1: Install PyInstaller

First, you need to install PyInstaller, a tool that freezes Python applications into stand-alone executables.

```bash
pip install pyinstaller
```

## Step 2: Prepare for Data Files

To ensure that your application can find assets like `logo.jpg` when it's packaged, a helper function in `utils.py` determines the correct path to the asset, whether the app is running from source or as a frozen executable. No changes are needed here.

## Step 3: Create the Executable

This step has two parts. First, find the data folder for the `pvlib` library, then run PyInstaller.

### Part A: Find the pvlib Data Path

Run the following command in your terminal (make sure your virtual environment is active). This will print the full path to the `pvlib` data directory needed for solar calculations.

```bash
python -c "import pvlib; import os; print(os.path.join(os.path.dirname(pvlib.__file__), 'data'))"
```

Copy the output path.
- On macOS/Linux, it will look like: `/path/to/your/venv/lib/python3.9/site-packages/pvlib/data`
- On Windows, it will look like: `C:\path\to\your\venv\Lib\site-packages\pvlib\data`

### Part B: Run PyInstaller

Now, run the PyInstaller command. **Replace `"PASTE_PVLIB_DATA_PATH_HERE"` with the actual path you copied from Part A.**

The `--add-data` separator is platform-specific: use a semicolon (`;`) on Windows and a colon (`:`) on macOS/Linux.

**On Windows:**
```bash
pyinstaller --name BatterijTerugverdientijdTool --onefile --add-data "logo.jpg;." --add-data "PASTE_PVLIB_DATA_PATH_HERE;pvlib/data" main.py
```

**On macOS / Linux:**
```bash
pyinstaller --name BatterijTerugverdientijdTool --onefile --add-data "logo.jpg:." --add-data "venv/lib/python3.13/site-packages/pvlib/data:pvlib/data" main.py
```

**Command Breakdown:**
*   `--name BatterijTerugverdientijdTool`: Sets the name of your final executable.
*   `--onefile`: Packages everything into a single executable file.
*   `--add-data "logo.jpg:."`: Bundles your `logo.jpg` into the executable (note the separator).
*   `--add-data "PASTE_PVLIB_DATA_PATH_HERE:pvlib/data"`: Bundles the essential `pvlib` data files into the executable.
*   `main.py`: Your application's entry point.

### About the Console Window (`--windowed` option)

By default, the executable will open a terminal (console) window to display progress and messages. If you want to create a purely graphical application that does not open this console, add the `--windowed` or `-w` flag to the command.

**Warning:** If you use `--windowed`, any `print()` statements will be hidden, and if the application fails to start (e.g., `config.ini` is missing), it may close silently without any error message. For this application, it is **recommended to not use `--windowed`** so that users can see the simulation progress.

## Step 4: Distribute Your Application

After running the command, PyInstaller will create a `dist` folder.

- On macOS, it contains `BatterijTerugverdientijdTool`.
- On Windows, it contains `BatterijTerugverdientijdTool.exe`.

To distribute your application, create a folder and include the following:

1.  **The Executable:** `dist/BatterijTerugverdientijdTool` (or `.exe` for Windows)
2.  **Configuration File:** `config.ini`
3.  **EPEX Data:** The `european_wholesale_electricity_price_data_hourly/` directory.
4.  **User Data:** The `wegdam/` directory containing the consumption/solar CSV files.

The final distribution folder should look like this:

```
/My_Packaged_App/
├── BatterijTerugverdientijdTool.exe  (the Windows executable)
├── config.ini
├── european_wholesale_electricity_price_data_hourly/
│   └── Netherlands.csv
└── wegdam/
    └── wegdam_extra_zon.csv
```

The user can then double-click the executable to run it.
