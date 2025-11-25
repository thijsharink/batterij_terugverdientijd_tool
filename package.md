# How to Package Your Application

This guide explains how to package your Python application into a single executable file using PyInstaller. This process will protect your source code and assets (like `logo.png`) while allowing users to configure the application via `config.ini` and provide their own CSV data.

## Step 1: Install PyInstaller

First, you need to install PyInstaller, a tool that freezes Python applications into stand-alone executables.

```bash
pip install pyinstaller
```

## Step 2: Prepare for Data Files

To ensure that your application can find assets like `logo.png` when it's packaged, we need a helper function. This function will determine the correct path to the asset, whether the app is running from source or as a frozen executable.

A new file, `utils.py`, will be created to house this function. The `visualizer.py` script will be modified to use this function. No other code changes are needed.

## Step 3: Create the Executable

This step is now in two parts. First, we need to find the data folder for the `pvlib` library, which is essential for solar calculations.

### Part A: Find the pvlib Data Path

Run the following command in your terminal (make sure your virtual environment is active). This will print the full path to the `pvlib` data directory.

```bash
python -c "import pvlib; import os; print(os.path.join(os.path.dirname(pvlib.__file__), 'data'))"
```

Copy the output path. It will look something like `/path/to/your/venv/lib/python3.9/site-packages/pvlib/data`.

### Part B: Run PyInstaller

Now, run the PyInstaller command. **Replace `"PASTE_PVLIB_DATA_PATH_HERE"` with the actual path you copied from Part A.**

```bash
pyinstaller --name BatterijTerugverdientijdTool --onefile --add-data "logo.jpg:." --add-data "venv/lib/python3.13/site-packages/pvlib/data:pvlib/data" main.py
```

**Command Breakdown:**

*   `--name BatterijTerugverdientijdTool`: Sets the name of your final executable.
*   `--onefile`: Packages everything into a single executable file.
*   `--add-data "logo.jpg:."`: Bundles your `logo.jpg` into the executable.
*   `--add-data "PASTE_PVLIB_DATA_PATH_HERE:pvlib/data"`: **This is the crucial new line.** It finds the essential data files from the `pvlib` library (like `Altitude.h5`) and bundles them into the correct `pvlib/data` folder inside your executable.
*   `main.py`: Your application's entry point.

## Step 4: Distribute Your Application

After running the command, PyInstaller will create a `dist` folder containing your executable: `BatterijTerugverdientijdTool`.

To distribute your application, create a folder and include the following:

1.  **The Executable:** `dist/BatterijTerugverdientijdTool`
2.  **Configuration File:** `config.ini`
3.  **EPEX Data:** The `european_wholesale_electricity_price_data_hourly/` directory.
4.  **User Data:** The `wegdam/` directory containing the consumption/solar CSV files.

The final distribution folder should look like this:

```
/My_Packaged_App/
├── BatterijTerugverdientijdTool  (the executable)
├── config.ini
├── european_wholesale_electricity_price_data_hourly/
│   └── Netherlands.csv
└── wegdam/
    └── wegdam_extra_zon.csv
```

The user can then run the `BatterijTerugverdientijdTool` executable from their terminal. The application will read the `config.ini` and the data from the `wegdam` and `european_wholesale_electricity_price_data_hourly` directories.
