from initialize import MakeScenarios as ms


def test_import_scenarios():
    scenarios = ms.from_excel("inputs/scenario_test.xlsx", which=["Reference"])

    assert type(scenarios) == dict
    return scenarios
