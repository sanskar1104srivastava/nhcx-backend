import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from nhcx.requests.outboundRequest import OutboundRequest
from nhcx.utils.bundleValidator import validateBundle
from scripts.payer_side_samples import build_send_payload, describe_workflow, list_workflows, load_fixture


class PayerSideSamplesTestCase(unittest.TestCase):
    def test_list_workflows_includes_supported_flows(self) -> None:
        self.assertEqual(
            {
                "insuranceplan",
                "coverageeligibility",
                "preauth",
                "claim",
                "communication",
                "paymentnotice",
                "task",
                "search",
            },
            set(list_workflows()),
        )

    def test_insuranceplan_uses_request_task_fixture(self) -> None:
        info = describe_workflow("insuranceplan")
        self.assertEqual("taskBundleInsurancePlanRequest-dummyPayer.json", info["fixture"])
        self.assertEqual("/insuranceplan/request", info["endpoint"])

    def test_paymentnotice_maps_to_existing_send_use_case(self) -> None:
        info = describe_workflow("paymentnotice")
        self.assertEqual("payment", info["useCase"])
        self.assertEqual("/paymentnotice/on_request", info["endpoint"])

    def test_reprocess_fixture_uses_dummy_payer_claim_identifier(self) -> None:
        fixture = load_fixture("task")
        task = fixture["entry"][0]["resource"]
        claimNumberInputs = [
            item["valueString"]
            for item in task.get("input", [])
            for coding in item.get("type", {}).get("coding", [])
            if coding.get("code") == "claimNumber"
        ]
        self.assertEqual(["7612345"], claimNumberInputs)

    def test_search_uses_task_status_request_shape(self) -> None:
        info = describe_workflow("search")
        self.assertEqual("taskBundleSearchRequest.json", info["fixture"])
        self.assertEqual("search", info["useCase"])
        self.assertEqual("/search/submit", info["endpoint"])
        fixture = load_fixture("search")
        task = fixture["entry"][0]["resource"]
        self.assertEqual("requested", task["status"])
        self.assertEqual("status", task["code"]["coding"][0]["code"])
        self.assertEqual("ClaimNumber", task["input"][0]["type"]["coding"][0]["code"])

    def test_all_workflow_payloads_match_send_request_contract(self) -> None:
        for workflow in list_workflows():
            with self.subTest(workflow=workflow):
                payload = build_send_payload(
                    workflow,
                    hospitalId="H1",
                    recipientCode="1000003538@hcx",
                    workflowId="1",
                )
                req = OutboundRequest(**payload)
                validateBundle(req.fhirBundle)


if __name__ == "__main__":
    unittest.main()
