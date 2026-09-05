# Efficient Biomass Supply Chain Design (Shell.ai Hackathon 2023)

A large-scale supply chain optimization pipeline built for the Shell.ai Hackathon
2023: forecast biomass availability at 2,417 harvesting sites, then site depots and
biorefineries and route biomass flows between them to minimize transport and
underutilization cost, subject to capacity and coverage constraints.

The challenge was to determine optimal locations to build depots and refineries for
biomass-to-energy production. It combined two problems: forecasting biomass
quantities for 2018 and 2019 from seven years of historical data, and an
optimization problem to place depots so as to minimize a cost objective. Given the
size of the input data, solving the full mathematical model directly with solvers
like Gurobi or CPLEX was impractical within the competition's time limit, so we
designed a batch data processing algorithm that trades strict optimality for a
solution obtainable in a reasonable timeframe.

**Result:** out of 200+ competing teams, this solution placed **3rd in its
category**, presented at the "Changemakers of Tomorrow" conference in Bangalore,
India.

## Problem

Given historical biomass yield (2010 to 2017) at 2,417 harvesting sites and the
pairwise distance matrix between all sites, the goal is to:

1. Forecast each site's biomass availability for 2018 and 2019.
2. Choose up to 25 depot locations and up to 5 biorefinery locations from those
   same sites.
3. Route biomass from harvesting sites to depots, and processed pellets from
   depots to biorefineries, so that at least 80% of forecasted biomass is
   processed each year, no depot or refinery exceeds its yearly capacity
   (20,000 for a depot, 100,000 for a refinery), and total transport plus
   underutilization cost is minimized.

## Approach

**Forecasting** (`forecast.ipynb`): fits an ARIMA model per harvesting site, grid
searching over `(p, d, q)` in `range(3)` each and picking the combination with the
lowest out-of-sample MSE on a train/test split of the 8-year history, then forecasts
2018 and 2019 biomass availability per site.

**Optimization** (`seq_solve.py`, `batch_solve.py`, `hackaton.ipynb`): the full
problem is a mixed-integer linear program (PuLP, solved with CPLEX) with continuous
flow variables and binary depot and refinery placement variables. At 2,417 sites the
full problem is too large to solve directly, so it's split into batches of 200 sites
and solved in two stages:

1. **Harvesting sites to depots**: each batch picks depot locations and flows,
   carrying forward which depots are already open and how much spare capacity they
   have (`used_depots`) so later batches can keep filling depots opened earlier
   instead of always opening new ones.
2. **Depots to biorefineries**: reads the depot assignments and quantities from
   stage 1 (`collected_biomass.csv`) and solves a second MILP to place biorefineries
   and route pellets from depots to refineries.

`seq_solve.py` is the refined sequential version that tracks depot state across
batches; `batch_solve.py` is an earlier parallelized version (one independent MILP
per batch, run concurrently via threads).

## Data

- `Biomass_history.csv` / `hackerank/dataset/Biomass_History.csv`: yearly biomass
  yield per site, 2010 to 2017.
- `hackerank/dataset/Distance_Matrix.csv`: pairwise distances between all 2,417
  sites.
- `hackerank/dataset/sample_submission.csv`: the competition's submission format.

## Output

`submission.csv`, `submission_forecast_2018.csv`, `submission_forecast_2019.csv`:
formatted per the competition schema (year, data type, source index, destination
index, value), covering the biomass forecasts, depot and refinery placements, and
flow quantities.

## Tech stack

Python, pandas, numpy, statsmodels (ARIMA), PuLP with CPLEX, threading.
