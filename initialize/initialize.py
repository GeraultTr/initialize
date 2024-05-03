import os
import pandas as pd
import pickle


class MakeScenarios:

    def from_table(file_path, which=[]):
        instructions = read_table(file_path)
        input_directory = os.path.dirname(file_path)

        if len(which) > 0:
            scenario_names = which
        else:
            scenario_names = [scenario_name for scenario_name in instructions.columns if scenario_name not in ("Input", "Input_type", "Explanation", "Type/ Unit", "Reference_value")]
        instructions_parameters = instructions.loc[instructions["Input_type"] == "parameter"]
        instructions_table_file = instructions.loc[instructions["Input_type"] == "input_tables"]
        instructions_initial_mtg_file = instructions.loc[instructions["Input_type"] == "input_mtg"]

        scenarios = {name: {
            "parameters": dict(zip(instructions_parameters["Input"], instructions_parameters[name].replace({'True': True, 'False': False}))) if len(instructions_parameters) > 0 else None,
            "input_tables": {var: read_table(os.path.join(input_directory, instructions_table_file.loc[instructions_table_file["Input"] == var][name][["t", var]]))
                             for var in instructions_table_file["Input"]} if len(instructions_table_file) > 0 else None,
            "input_mtg": {var: pickle.load(open(os.path.join(input_directory, instructions_initial_mtg_file.loc[instructions_initial_mtg_file["Input"] == var][name]), "rb"))
                          for var in instructions_initial_mtg_file["Input"]} if len(instructions_initial_mtg_file) > 0 else None
                            }
                     for name in scenario_names}
        return scenarios


def read_table(file_path):
    if file_path.lower().endswith((".csv", ".xlsx")):
        # Add more types then if necessary
        if file_path.lower().endswith(".xlsx"):
            return pd.read_excel(file_path)

        elif file_path.lower().endswith(".csv"):
            return pd.read_csv(file_path)
    else:
        raise TypeError("Only tables are allowed")
