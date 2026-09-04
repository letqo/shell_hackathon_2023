import pandas as pd
from pulp import *
from threading import Thread

def solve_batch(batch_num, batch_increment,biomass_data, distance_matrix):

    surplus = 0
    message = ""

    if batch_num == ((2417//batch_increment)-1)*batch_increment:
        surplus = 17

    # Step 2: Read the provided datasets
    biomass_data = biomass_data.iloc[batch_num:batch_num+batch_increment+surplus,:4]

    distance_matrix = distance_matrix.iloc[batch_num:batch_num+batch_increment+surplus,1+batch_num:1+batch_num+batch_increment+surplus]
       
    # Step 3: Create PuLP variables and the optimization problem
    model =  LpProblem("Waste_to_Energy_Optimization",LpMinimize)

    # Decision Variables
    num_harvesting_sites = len(biomass_data)
    num_depots = 25
    num_biorefineries = 5

    # Amount of biomass transported from each Harvesting Site to each Depot (continuous variable)
    biomass_demand_supply = LpVariable.dicts("biomass",[(i, j) for i in range(num_harvesting_sites) \
                                                        for j in range(num_harvesting_sites)], lowBound=0, cat=LpContinuous) 
    # Amount of biomass transported from each Depot to each refinery (continuous variable)
    pellet_demand_supply = LpVariable.dicts("pellet",[(j, k) for j in range(num_harvesting_sites) \
                                                       for k in range(num_harvesting_sites)], lowBound=0, cat=LpContinuous)
    
    # Binary variables representing whether Depot j and Biorefinery k are placed or not
    depot = LpVariable.dicts("depot",[j for j in range(num_harvesting_sites)], cat=LpBinary)
    refinery = LpVariable.dicts("refinery",[k for k in range(num_harvesting_sites)], cat=LpBinary)

    # The objective function
    # Constants
    a = 0.001
    b = 1
    c = 1
    cap_depot = int(20000/batch_increment)
    cap_refinery = int(100000/batch_increment)
    # Objective function
    cost_transport = lpSum(distance_matrix.iloc[i, j] * biomass_demand_supply[i, j] for i in range(num_harvesting_sites) \
                                                                                    for j in range(num_harvesting_sites))
    cost_transport += lpSum(distance_matrix.iloc[j, k] * pellet_demand_supply[j, k] for j in range(num_harvesting_sites)\
                                                                                    for k in range(num_harvesting_sites))

    cost_underutilization = lpSum((depot[j]*cap_depot - lpSum(biomass_demand_supply[i, j] for i in range(num_harvesting_sites))) \
                                                                                          for j in range(num_harvesting_sites)) \
                           + lpSum((refinery[k]*cap_refinery - lpSum(pellet_demand_supply[j, k] for j in range(num_harvesting_sites))) \
                                                                                          for k in range(num_harvesting_sites))

    # Objective function
    model += a * cost_transport + c * cost_underutilization, "Total_Cost"

    # Constraints
    # Constraint: Biomass demand from each Harvesting Site i must be less than or equal to its forecasted biomass availability
    for i in range(num_harvesting_sites):
        model += lpSum(biomass_demand_supply[i, j] for j in range(num_harvesting_sites)) <= biomass_data[f'{biomass_data.columns[3]}'].iloc[i]

    # Constraint: Total biomass reaching each preprocessing depot j must be less than or equal to its yearly processing capacity (20,000)
    for j in range(num_harvesting_sites):
        model += lpSum(biomass_demand_supply[i, j] for i in range(num_harvesting_sites)) <= depot[j]*cap_depot

    # Constraint: Total pellets reaching each biorefinery k must be less than or equal to its yearly processing capacity (100,000)
    for k in range(num_harvesting_sites):
        model += lpSum(pellet_demand_supply[j, k] for j in range(num_harvesting_sites)) <= refinery[k]*cap_refinery

    # Constraint: Limit the number of depots to be less than or equal to 25
    model += lpSum(depot[j] for j in range(num_harvesting_sites)) <= num_depots

    # Constraint: Limit the number of biorefineries to be less than or equal to 5
    model += lpSum(refinery[k] for k in range(num_harvesting_sites)) <= num_biorefineries

    # Constraint: At least 80% of the total forecasted biomass is processed by biorefineries each year
    total_forecasted_biomass = sum(biomass_data[f'{biomass_data.columns[3]}'])
    total_processed_biomass = lpSum(biomass_demand_supply[i, j] for i in range(num_harvesting_sites) for j in range(num_harvesting_sites))
    model += total_processed_biomass >= 0.8 * total_forecasted_biomass

    # Constraint: Total biomass entering each preprocessing depot should be equal to the total amount of pellets exiting that depot (within tolerance limit)
    for j in range(num_harvesting_sites):
        model += lpSum(biomass_demand_supply[i, j] for i in range(num_harvesting_sites)) \
                 - lpSum(pellet_demand_supply[j, k] for k in range(num_harvesting_sites)) == 0


    # Solve the problem
    solver = CPLEX_CMD()
    model.solve(solver=solver)
    message += f"Status {batch_num}: {LpStatus[model.status]}\n"

    #    
    for v in model.variables():
        if v.varValue!=0:
            message += f'{v.name} = {v.varValue}\n'

    #    
    # Calculate the sum of values for each decision variable
    biomass_sum = lpSum(biomass_demand_supply[i, j].varValue for i in range(num_harvesting_sites) for j in range(num_harvesting_sites))
    pellet_sum = lpSum(pellet_demand_supply[j, k].varValue for j in range(num_harvesting_sites) for k in range(num_harvesting_sites))
    depot_sum = lpSum(depot[j].varValue for j in range(num_harvesting_sites))
    refinery_sum = lpSum(refinery[k].varValue for k in range(num_harvesting_sites))

    message += f"Total biomass harvested: {biomass_sum}\n"
    message += f"Total pellets processed: {pellet_sum}\n"
    message += f"Nombre de dépots: {depot_sum}\n"
    message += f"Nomber of refineries : {refinery_sum}\n"

    with open(f'Report_batch_{batch_num}_to_{batch_num+batch_increment}.txt','w') as file:
        file.write(message)

# Load the data outside the threads
biomass_data = pd.read_csv('hackerank/dataset/Biomass_History.csv')
distance_matrix = pd.read_csv('hackerank/dataset/Distance_Matrix.csv')
batch_increment = 200

threads = []
for i in range(0, (200// batch_increment - 1) * batch_increment + 1, batch_increment):
    # Create separate copies of data for each thread
    batch_biomass_data = biomass_data.copy()
    batch_distance_matrix = distance_matrix.copy()

    t = Thread(target=solve_batch, args=(i, batch_increment,batch_biomass_data, batch_distance_matrix))
    t.start()
    threads.append(t)

for t in threads:
    t.join()


