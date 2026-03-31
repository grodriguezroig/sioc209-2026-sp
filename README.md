# Deep Learning for Geo and Environmental Science

Course content and material for SIOC 209

## Usage

### Building the slides

The slides require a RISE which needs an older version of Jupyter Notebook. To build the slides, you should:

1. Clone this repository
2. Run `conda create -n <sio209_dev> -c conda-forge python=3.10 xarray netcdf4 cartopy jupyter-book rise jupyter_contrib_nbextensions notebook==6.5.6`
3. Activate your dev environment
3. Run `pip install tensorflow-metal scikit-learn gpflow` inside that environment
3. (Optional) Edit the slides source files located in the `sioc209-2026-sp/slides/` directory
4. Run `jupyter nbconvert --to slides sioc209-2026-sp/slides/*.ipynb --reveal-prefix=reveal.js --SlidesExporter.reveal_scroll=True`


## Contributors

We welcome and recognize all contributions. You can see a list of current contributors in the [contributors tab](https://github.com/duncanwp/sioc209-2026-sp/graphs/contributors).

