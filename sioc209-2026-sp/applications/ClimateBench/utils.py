import os
import numpy as np
import pandas as pd
import xarray as xr
from eofs.xarray import Eof

# Data path resolution order:
#   1. CLIMATEBENCH_DATA_PATH environment variable (if set)
#   2. ./data/train_val/  (local clone — works if you downloaded the data)
#   3. Google-Drive path used on Colab (mount Drive first, see assignment notebook)
#
# On Google Colab, run this *before* importing utils:
#   from google.colab import drive
#   drive.mount('/content/drive')
#   os.environ["CLIMATEBENCH_DATA_PATH"] = "/content/drive/Shareddrives/SOPC-209 Data/ClimateBench/train_val_updated/"

_default_local = os.path.join(os.path.dirname(__file__), "data", "train_val")
data_path = os.environ.get("CLIMATEBENCH_DATA_PATH", _default_local)

# Ensure trailing separator so  data_path + f"inputs_{file}.nc"  works
if not data_path.endswith(os.sep):
    data_path += os.sep

if not os.path.isdir(data_path):
    import warnings
    warnings.warn(
        f"ClimateBench data directory not found at:\n  {data_path}\n"
        "Set the CLIMATEBENCH_DATA_PATH environment variable or download the data into\n"
        f"  {_default_local}\n"
        "See the Google Drive link on Canvas for the dataset."
    )

min_co2 = 0.
max_co2 = 9500
def normalize_co2(data):
    return data / max_co2

def un_normalize_co2(data):
    return data * max_co2

min_ch4 = 0.
max_ch4 = 0.8
def normalize_ch4(data):
    return data / max_ch4

def un_normalize_ch4(data):
    return data * max_ch4


def create_predictor_data(data_sets, n_eofs=5):
    """
    Args:
        data_sets list(str): names of datasets
        n_eofs (int): number of eofs to create for aerosol variables
    """
        
    # Create training and testing arrays
    if isinstance(data_sets, str):
        data_sets = [data_sets]
    X = xr.concat([xr.open_dataset(data_path + f"inputs_{file}.nc") for file in data_sets], dim='time')
    X = X.assign_coords(time=np.arange(len(X.time)))

    # Compute EOFs for BC
    bc_solver = Eof(X['BC'])
    bc_eofs = bc_solver.eofsAsCorrelation(neofs=n_eofs)
    bc_pcs = bc_solver.pcs(npcs=n_eofs, pcscaling=1)

    # Compute EOFs for SO2
    so2_solver = Eof(X['SO2'])
    so2_eofs = so2_solver.eofsAsCorrelation(neofs=n_eofs)
    so2_pcs = so2_solver.pcs(npcs=n_eofs, pcscaling=1)

    # Convert to pandas
    bc_df = bc_pcs.to_dataframe().unstack('mode')
    bc_df.columns = [f"BC_{i}" for i in range(n_eofs)]

    so2_df = so2_pcs.to_dataframe().unstack('mode')
    so2_df.columns = [f"SO2_{i}" for i in range(n_eofs)]

    # Bring the emissions data back together again and normalise
    inputs = pd.DataFrame({
        "CO2": normalize_co2(X["CO2"].data),
        "CH4": normalize_ch4(X["CH4"].data)
    }, index=X["CO2"].coords['time'].data)

    # Combine with aerosol EOFs
    inputs = pd.concat([inputs, bc_df, so2_df], axis=1)
    return inputs, (so2_solver, bc_solver)


def get_test_data(file, eof_solvers, n_eofs=5):
    """
    Args:
        file str: name of datasets
        n_eofs (int): number of eofs to create for aerosol variables
        eof_solvers (Eof_so2, Eof_bc): Fitted Eof objects to use for projection
    """
        
    # Create training and testing arrays
    X = xr.open_dataset(data_path + f"inputs_{file}.nc")
        
    so2_pcs = eof_solvers[0].projectField(X["SO2"], neofs=5, eofscaling=1)
    so2_df = so2_pcs.to_dataframe().unstack('mode')
    so2_df.columns = [f"SO2_{i}" for i in range(n_eofs)]

    bc_pcs = eof_solvers[1].projectField(X["BC"], neofs=5, eofscaling=1)
    bc_df = bc_pcs.to_dataframe().unstack('mode')
    bc_df.columns = [f"BC_{i}" for i in range(n_eofs)]

    # Bring the emissions data back together again and normalise
    inputs = pd.DataFrame({
        "CO2": normalize_co2(X["CO2"].data),
        "CH4": normalize_ch4(X["CH4"].data)
    }, index=X["CO2"].coords['time'].data)

    # Combine with aerosol EOFs
    inputs = pd.concat([inputs, bc_df, so2_df], axis=1)
    return inputs


def create_predictdand_data(data_sets):
    if isinstance(data_sets, str):
        data_sets = [data_sets]
    Y = xr.concat([xr.open_dataset(data_path + f"outputs_{file}.nc") for file in data_sets], dim='time').mean("member")
    # Convert the precip values to mm/day
    Y["pr"] *= 86400
    Y["pr90"] *= 86400
    return Y


def get_rmse(truth, pred):
    weights = np.cos(np.deg2rad(truth.lat))
    return np.sqrt(((truth - pred)**2).weighted(weights).mean(['lat', 'lon'])).data

def plot_diff(truth, pred, title):
    from matplotlib import colors
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    # setup the normalization and the colormap
    divnorm = colors.TwoSlopeNorm(vmin=-2., vcenter=0., vmax=5)
    diffnorm = colors.TwoSlopeNorm(vmin=-2., vcenter=0., vmax=2)

    ## Temperature
    proj = ccrs.PlateCarree()
    fig = plt.figure(figsize=(18, 3))
    fig.suptitle(title)

    # Test
    plt.subplot(131, projection=proj)
    truth.sel(time=slice(2050,None)).mean('time').plot(cmap="coolwarm", norm=divnorm,
                                cbar_kwargs={"label":"Temperature change / K"})
    plt.gca().coastlines()
    plt.setp(plt.gca(), title='True')

    # Emulator
    plt.subplot(132, projection=proj)
    pred.isel(time=slice(65,None)).mean('time').plot(cmap="coolwarm", norm=divnorm,
                        cbar_kwargs={"label":"Temperature change / K"})
    plt.gca().coastlines()
    plt.setp(plt.gca(), title='GP posterior mean')

    # Difference
    difference = truth - pred.data
    plt.subplot(133, projection=proj)
    difference.isel(time=slice(65,None)).mean('time').plot(cmap="bwr", norm=diffnorm,
                    cbar_kwargs={"label":"Temperature change / K"})
    plt.gca().coastlines()
    plt.setp(plt.gca(), title='Difference')