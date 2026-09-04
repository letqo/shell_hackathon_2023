import pandas as pd
from pulp import *

total_objective = 0
# depot_index_list = []
# biomass_quantities = [] 
batch_increment = 200
depots_holding = dict() # To store the depots and their biomass feed for the next script

def solve_batch(batch_num, used_depots, num_dep_satur):

    """
    used_depots : dictionary holding the depots already used and their corresponding biomass holding
    num_dep_satur : number of depots that have already been saturated in capacity
    
    """
    # global depot_index_list, biomass_quantities

    global batch_increment,total_objective, depots_holding
    global distance_matrix, biomass_data

    surplus = 0 # Pour les 17 restants en plus (en fait tout excédant)
    message = "" # Remplace les prints, le rapport pour chaque batch sera mis dans un fichier txt

    if batch_num == ((2417//batch_increment)-1)*batch_increment: #Ajustement pour le dernier batch
        surplus = 18

    previous_depots = list(used_depots.keys())

    # Step 3: Create PuLP variables and the optimization problem
    model =  LpProblem("Waste_to_Energy_Optimization",LpMinimize)

    ####################################### Parameters ###############################################

    num_harvesting_sites = list(range(batch_num,batch_num+batch_increment+surplus))
    num_depots = 25-num_dep_satur # Ajust the max number of depots authorized for each batch

    depots_indices = num_harvesting_sites.copy()
    depots_indices.extend(previous_depots)

    ###################################### Decision Variables ############################################

    # Amount of biomass transported from each Harvesting Site to each Depot (continuous variable)
    ## !!!! problem with the j indices (! Solved)
    biomass_demand_supply = LpVariable.dicts("biomass_demand_supply",[(i, j) for i in num_harvesting_sites \
                                                        for j in depots_indices], lowBound=0, cat=LpContinuous)

    # Binary variables representing whether Depot j and Biorefinery k are placed or not
    depot = LpVariable.dicts("depot_location", depots_indices, cat=LpBinary)

    #################################### Objective function ############################################

    # Constants
    a = 0.001
    c = 1
    cap_depot = dict([(j,20000) for j in num_harvesting_sites])
    cap_depot.update(used_depots)

    cost_transport = lpSum(distance_matrix.iloc[i, j] * biomass_demand_supply[i, j] for i in num_harvesting_sites \
                                                                                    for j in depots_indices)
    cost_underutilization = lpSum(depot[j]*cap_depot[j] for j in depots_indices) - \
                          lpSum(biomass_demand_supply[i, j] for i in num_harvesting_sites \
                                                            for j in depots_indices)
    # Objective function
    objective = a * cost_transport + c * cost_underutilization
    model += objective, "Total_Cost"

    ####################################### Constraints ###############################################

    # Constraint: Biomass demand from each Harvesting Site i must be less than or equal to its forecasted biomass availability
    for i in num_harvesting_sites:
        model += lpSum(biomass_demand_supply[i, j] for j in depots_indices) <= biomass_data[f'{biomass_data.columns[3]}'].iloc[i]

    # Constraint: Total biomass reaching each preprocessing depot j must be less than or equal to its yearly processing capacity (20,000)
    for j in depots_indices:
        model += lpSum(biomass_demand_supply[i, j] for i in num_harvesting_sites) <= depot[j]*cap_depot[j]

    # Constraint: Limit the number of depots to be less than or equal to 25
    model += lpSum(depot[j] for j in depots_indices) <= num_depots

    # Constraint: At least 80% of the total forecasted biomass is processed by biorefineries each year
    total_forecasted_biomass = sum(biomass_data[f'{biomass_data.columns[3]}'])
    total_processed_biomass = lpSum(biomass_demand_supply[i, j] for i in num_harvesting_sites for j in depots_indices)
    model += total_processed_biomass >= 0.8 * total_forecasted_biomass

    #Constraint: Saturate the already used depots first
    for j in previous_depots:
        model += depot[j] == 1.0

    #################################### Solving the problem ############################################
    
    solver = CPLEX_CMD()
    model.solve(solver=solver)
    message += f"Status {batch_num}: {LpStatus[model.status]}\n"

    ####################################### Reporting ###############################################

    # Calculate the sum of values for each decision variable
    biomass_sum = lpSum(biomass_demand_supply[i, j].varValue for i in num_harvesting_sites for j in num_harvesting_sites)
    depot_sum = lpSum(depot[j].varValue for j in num_harvesting_sites)

    marge = 50 # Remaining amount to consider the depot saturated


    for v in model.variables():

        if v.varValue!=0 and 'depot' not in v.name:
            #Report the biomass_demand_supply values
            splitted_name = (v.name).split("_")
            #Imagine if the sink(depot) is a previous one, we don't have to add batch_num anymore
            source = int(splitted_name[-2].lstrip('(').rstrip(','))
            sink = int(splitted_name[-1].rstrip(')'))
    
            message += f"2018,{'_'.join(splitted_name[0:-2])},{source},{sink},{v.varValue}\n"
        
        if 'depot' in v.name:
            #Report the depot_location values
            if v.varValue <= 1.0 and v.varValue >= 0.8:
                index = int((v.name).split('_')[-1])
                holding = lpSum(biomass_demand_supply[i, index] for i in num_harvesting_sites)
                satur = 20000 - marge
                if index in previous_depots:
                    # If the depot has been used in previous batches
                    if cap_depot[index] > marge:
                        # If the remaining capacity of the depot still exceeds the margin, there's still something left
                        # to consume
                        satur = cap_depot[index]-marge
                    else:
                        # Otherwise erase it from the memo
                        del used_depots[index]
                else:
                    # If the depot has NOT been used in previous batches
                    splitted_name = (v.name).split("_")
                    # depot_index_list.append(index)
                    depots_holding[index] = holding.value()
                    message += f"2018,{'_'.join(splitted_name[0:2])},{index},,\n"
                if holding.value() < satur and holding.value() > 0:
                    used_depots[index] = satur-holding.value()
                    if index in previous_depots:
                        depots_holding[index]+=holding.value()
                else:
                    num_dep_satur+=1

    total_objective += objective.value()
    message += f"Objective: {objective.value()}\n"
    message += f"Total biomass harvested: {biomass_sum}\n"
    message += f"Total number of depots : {depot_sum}\n"

    with open(f'Report_Step_{batch_num}_to_{batch_num+batch_increment+surplus}.txt','w') as file:
        file.write(message)

    return used_depots,num_dep_satur

# Loading the dataset one time for all
biomass_data = pd.read_csv('Biomass_History.csv')
distance_matrix = pd.read_csv('hackerank/dataset/Distance_Matrix.csv')
used_depots = dict()
num_dep_satur = 0

for i in range(0, (2417 // batch_increment - 1) * batch_increment + 1, batch_increment):
    used_depots,num_dep_satur = solve_batch(i,used_depots,num_dep_satur)
    print(used_depots)

print(f"Total objective : {total_objective}")

pd.DataFrame({"depots":list(depots_holding.keys()),
              "quantities":list(depots_holding.values())}).to_csv("collected_biomass.csv")



