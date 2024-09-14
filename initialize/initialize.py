import os
import pandas as pd
import numpy as np
import pickle
from SALib.sample import saltelli
from openalea.mtg import MTG
from openalea.mtg.traversal import pre_order2
import xml.etree.ElementTree as ET


class MakeScenarios:

    def from_table(file_path, which=[]):
        instructions = read_table(file_path, index_col="Input")
        input_directory = os.path.dirname(file_path)

        if len(which) > 0:
            scenario_names = which
        else:
            scenario_names = [scenario_name for scenario_name in instructions.columns if scenario_name not in ("Input", "Input_type", "Dedicated_to", "Organ_label", "Explanation", "Type/ Unit", "Reference_value")]

        instructions_parameters = instructions.loc[instructions["Input_type"] == "parameter"]
        targeted_models = list(set(instructions_parameters["Dedicated_to"].values))

        # This accounts for different cases of parameter editing for different models
        subdict_of_parameters = {}
        for name in scenario_names:
            subdict_of_parameters.update({name: {}})
            for model in targeted_models:
                subdict_of_parameters[name].update({model: {}})
                table_extract = instructions_parameters[instructions_parameters["Dedicated_to"] == model]
                label = list(set(table_extract["Organ_label"].values))[0]
                # This accounts for the case where passed parameters to every models have to be encapsulated in a Organ-labelled dict
                if label is not None:
                    subdict_of_parameters[name][model].update(
                        {label: dict(zip(table_extract[name].index.values, table_extract[name].replace({'True': True, 'False': False, 'None': None})))}
                    )
                else:
                    subdict_of_parameters[name][model].update(
                        dict(zip(table_extract[name].index.values, table_extract[name].replace({'True': True, 'False': False, 'None': None})))
                    )

        instructions_table_file = instructions.loc[instructions["Input_type"] == "input_tables"]
        instructions_initial_mtg_file = instructions.loc[instructions["Input_type"] == "input_mtg"]
        scenarios = {name: {
            "parameters": subdict_of_parameters[name],
            "input_tables": {var: read_table(os.path.join(input_directory, str(instructions_table_file[name][var])), index_col="t")[var] 
                             for var in instructions_table_file.index.values if not pd.isna(instructions_table_file[name][var])} if len(instructions_table_file) > 0 else None,
            "input_mtg": {var: read_mtg(os.path.join(input_directory, str(instructions_initial_mtg_file[name][var]))) if not pd.isna(instructions_initial_mtg_file[name][var]) 
                          else None for var in instructions_initial_mtg_file.index.values} if len(instructions_initial_mtg_file) > 0 else None}
                     for name in scenario_names}

        return scenarios

    def from_factorial_plan(file_path, save_scenarios=True, N=10):
        factorial_plan = read_table(file_path, index_col="Input")
        input_directory = os.path.dirname(file_path)
        reference_dirpath = os.path.join(input_directory, "Scenarios_24_05.xlsx")
        reference_scenario = read_table(reference_dirpath, index_col="Input")
        reference_scenario = reference_scenario[["Input_type", "Dedicated_to", "Organ_label", "Explanation", "Type/ Unit", "Reference_value", "Reference_Fischer"]]

        SA_problem = {}
        
        factors = factorial_plan.index.to_list()
        SA_problem["num_vars"] = len(factors)
        SA_problem["names"] = factors
        SA_problem["bounds"] = factorial_plan[["Min", "Max"]].values.tolist()
        
        param_values = saltelli.sample(SA_problem, N=N, calc_second_order=True)
        scenario_names = [f"SA{i}" for i in range(len(param_values))]

        # Now produce the dataframe containing all the scenarios as rows, through an edition of the reference
        SA_scenarios = reference_scenario
        for k in range(len(param_values)):
            edited_scenario = reference_scenario["Reference_Fischer"].to_dict()
            for f in range(len(param_values[k])):
                edited_scenario[factors[f]] = param_values[k][f]
            SA_scenarios[scenario_names[k]] = edited_scenario

        output_filename = os.path.join(input_directory, "Scenarios_SA.xlsx")
        if save_scenarios:
            SA_scenarios.to_excel(output_filename)

        return SA_problem, output_filename, scenario_names



def read_table(file_path, index_col=None):
    if file_path.lower().endswith((".csv", ".xlsx")):
        # Add more types then if necessary
        if file_path.lower().endswith(".xlsx"):
            return pd.read_excel(file_path, index_col=index_col)

        elif file_path.lower().endswith(".csv"):
            return pd.read_csv(file_path, index_col=index_col, sep=";|,", engine="python")
    elif file_path == 'None':
        return None
    else:
        raise TypeError("Only tables are allowed")
    

def read_mtg(file_path):
    """
    General reader for MTG from native mtg file fromat or rsml xml format
    """
    if file_path.endswith(".pckl"):
        with open(file_path, "rb") as f:
            g = pickle.load(f)
    elif file_path.endswith(".rsml"):
        g = mtg_from_rsml(file_path)

    return g
    

def mtg_from_rsml(file_path: str, length_unit_conversion_factor = 54.0e-6, min_length=4e-3, diameter_filter_threshold: float = 0.5):
    """
    param: min_lengt in m
    """

    polylines, properties, functions = read_rsml(file_path)

    for f, v in functions.items():
        functions[f] = [[value * length_unit_conversion_factor if value else None for value in l ] for l in v]
    
    origin = polylines[0][0]

    polylines = [[[(i[j] - origin[j]) * length_unit_conversion_factor for j in range(len(origin))] for i in k] for k in polylines]

    if len(polylines[0][0]) == 2:
        flat_rsml = True
    elif len(polylines[0][0]) == 3:
        flat_rsml = False
    else:
        raise SyntaxError("Error in RSML file format, wrong number of coordinates")

    # We create an empty MTG:
    g = MTG()

    # We define the first base element as an empty element:
    if flat_rsml:
        x1, y1 = polylines[0][0]
        z1 = 0
    else:
        x1, y1, z1 = polylines[0][0]

    r1 = functions["diameter"][0][0] / 2.

    id_segment = g.add_component(g.root, label='Segment',
                                 type="Base_of_the_root_system",
                                 x1=x1,
                                 x2=x1,
                                 y1=y1,
                                 y2=y1,
                                 z1=-z1,
                                 z2=-z1,
                                 radius1=r1,
                                 radius2=r1,
                                 radius=r1,
                                 length=0,
                                 order=1
                                 )
    base_segment = g.node(id_segment)

    # We initialize an empty dictionary that will be used to register the vid of the mother elements:
    index_pointer_in_mtg = {}
    # We initialize the first mother element:
    mother_element = base_segment

    if flat_rsml:
        print("Opening 2D RSML...")
    else: 
        print("Opening 3D RSML...")
    
    # For each root axis:
    for l, line in enumerate(polylines):
        mean_radius_axis = np.mean([k for k in functions["diameter"][l] if k]) / 2
        
        # We initialize the first dictionary within the main dictionary:
        index_pointer_in_mtg[l] = {}
        # If the root axis is not the main one of the root system:
        if l > 0:
            # We define the mother element of the current lateral axis according to the properties of the RSML file:
            parent_axis_index = properties["parent-poly"][l]
            if "parent-node" in properties.keys():
                parent_node_index = properties["parent-node"][l]
            else:
                insertion_distances = [np.sqrt((x-line[0][0])**2 + (y-line[0][1])**2 + (z-line[0][2])**2) for (x, y, z) in polylines[parent_axis_index]]
                parent_node_index = insertion_distances.index(min(insertion_distances))

            mother_element = g.node(index_pointer_in_mtg[parent_axis_index][parent_node_index])

        # For each root element:
        for i in range(1,len(line)):
            # We define the x,y,z coordinates and the radius of the starting and ending point:
            if flat_rsml:
                x1, y1 = line[i-1]
                z1 = 0
                x2, y2 = line[i]
                z2 = 0
            else:
                x1, y1, z1 = line[i-1]
                x2, y2, z2 = line[i]

            if not functions["diameter"][l][i - 1]:
                r1 = mean_radius_axis
            else:
                r1 = functions["diameter"][l][i - 1] / 2

            if not functions["diameter"][l][i]:
                r2 = mean_radius_axis
            else:
                r2 = functions["diameter"][l][i] / 2

            # Filtering cases where incoherent high or low diameters have been annotated
            if r1 > mean_radius_axis * (1 + diameter_filter_threshold) or r1 < mean_radius_axis * (1 - diameter_filter_threshold):
                r1 = mean_radius_axis
            
            if r2 > mean_radius_axis * (1 + diameter_filter_threshold) or r2 < mean_radius_axis* (1 - diameter_filter_threshold):
                r2 = mean_radius_axis
                
            

            # The length of the root element is calculated from the x,y,z coordinates:
            length=np.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)

            # We define the edge type ('<': adding a root element on the same axis, '+': adding a lateral root):
            if i==1 and l > 0:
                # If this is the first element of the axis, and this is not the collar point, this element is a ramification.
                edgetype="+"
                order = mother_element.order + 1
            else:
                edgetype="<"
                order = mother_element.order
            # We define the label (Apex or Segment):
            if i == len(line) - 1:
                label="Apex"
            else:
                label="Segment"

            if mother_element.length < min_length and edgetype == "<":
                mother_element.x2 = x2
                mother_element.y2 = y2
                mother_element.z2 = -z2
                mother_element.radius = (mother_element.radius + r2) / 2
                mother_element.r2 = r2
                mother_element.length = np.sqrt(  (mother_element.x2-mother_element.x1)**2 
                                                + (mother_element.y2-mother_element.y1)**2 
                                                + (mother_element.z2-mother_element.z1)**2)
                if label == "Apex":
                    mother_element.label = "Apex"
                
                index_pointer_in_mtg[l][i]=mother_element.index()
            else:
                # We finally add the new root element to the previously-defined mother element:
                new_child = mother_element.add_child(edge_type=edgetype,
                                                    label=label,
                                                    type="Normal_root_after_emergence",
                                                    x1=x1,
                                                    x2=x2,
                                                    y1=y1,
                                                    y2=y2,
                                                    z1=-z1,
                                                    z2=-z2,
                                                    radius1=r1,
                                                    radius2=r2,
                                                    radius=(r1+r2)/2,
                                                    length=length,
                                                    order=order)
                # We record the vertex ID of the current root element:
                vid = new_child.index()
                # We add the vid to the dictionary:
                index_pointer_in_mtg[l][i]=vid
                # And we now consider current element as the mother element for the next iteration on this axis:
                mother_element = new_child
    
    # Finally, we filter diameters that might have remained too high because whole axis was wrong
    per_order_mean_diameters = {order: np.mean([g.property("radius")[k] for k in g.vertices() if k != 0 and g.property("order")[k] == order]) for order in [1, 2, 3, 4, 5]}

    root_gen = g.component_roots_at_scale_iter(g.root, scale=1)
    root = next(root_gen)

    for vid in pre_order2(g, root):
        n = g.node(vid)
        parent = n.parent()
        if parent:
            if n.radius > parent.radius * (1 + diameter_filter_threshold):
                n.radius = per_order_mean_diameters[n.order]

    return g


def read_rsml(name: str):
    """Parses the RSML file into:

    Args:
    name(str): file name of the rsml file

    Returns:
    (list, dict, dict):
    (1) a (flat) list of polylines, with one polyline per root
    (2) a dictionary of properties, one per root, adds "parent_poly" holding the index of the parent root in the list of polylines
    (3) a dictionary of functions
    """
    root = ET.parse(name).getroot()
    plant = root[1][0]
    polylines = []
    properties = {}
    functions = {}
    for elem in plant.iterfind('root'):
        (polylines, properties, functions) = parse_rsml_(elem, polylines, properties, functions, -1)

    return polylines, properties, functions


def parse_rsml_(organ: ET, polylines: list, properties: dict, functions: dict, parent: int):
    """ Recursivly parses the rsml file, used by read_rsml """
    for poly in organ.iterfind('geometry'):  # only one
        polyline = []
        for p in poly[0]:  # 0 is the polyline
            n = p.attrib
            newnode = [float(n['x']), float(n['y']), float(n['z'])]
            polyline.append(newnode)
        polylines.append(polyline)
        properties.setdefault("parent-poly", []).append(parent)

    for prop in organ.iterfind('properties'):
        for p in prop:  # i.e legnth, type, etc..
            try:
                value = float(p.attrib['value'])
            except ValueError:
                value = p.attrib['value']
            properties.setdefault(str(p.tag), []).append(value)


    for funcs in organ.iterfind('functions'):
        for fun in funcs:
            samples = []
            for sample in fun.iterfind('sample'):
                try:
                    value = float(sample.attrib['value'])
                except ValueError:
                    value = None
                samples.append(value)
            functions.setdefault(str(fun.attrib['name']), []).append(samples)

    pi = len(polylines) - 1
    for elem in organ.iterfind('root'):  # and all laterals
        polylines, properties, functions = parse_rsml_(elem, polylines, properties, functions, pi)

    return polylines, properties, functions

