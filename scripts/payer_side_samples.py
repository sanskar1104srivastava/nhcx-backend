import json
import pathlib
from typing import Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "fixtures"

WORKFLOW_API_DETAILS: Dict[str, Dict[str, str]] = {
    "insuranceplan": {
        "fixture": "taskBundleInsurancePlanRequest-dummyPayer.json",
        "useCase": "insuranceplan",
        "endpoint": "/insuranceplan/request",
    },
    "coverageeligibility": {
        "fixture": "coverageEligibilityRequestBundle-dummyPayer.json",
        "useCase": "coverageeligibility",
        "endpoint": "/coverageeligibility/check",
    },
    "preauth": {
        "fixture": "claimBundlePreauth-dummyPayer.json",
        "useCase": "preauth",
        "endpoint": "/preauth/submit",
    },
    "claim": {
        "fixture": "claimBundleClaim-dummyPayer.json",
        "useCase": "claim",
        "endpoint": "/claim/submit",
    },
    "predetermination": {
        "fixture": "claimBundlePredetermination-dummyPayer.json",
        "useCase": "predetermination",
        "endpoint": "/predetermination/submit",
    },
    "communication": {
        "fixture": "taskBundleCommunicationResponse-dummyPayer.json",
        "useCase": "communication",
        "endpoint": "/communication/on_request",
    },
    "paymentnotice": {
        "fixture": "taskBundlePaymentNoticeResponse.json",
        "useCase": "payment",
        "endpoint": "/paymentnotice/on_request",
    },
    "task": {
        "fixture": "taskBundleReprocessRequest.json",
        "useCase": "task",
        "endpoint": "/task/submit",
    },
    "search": {
        "fixture": "taskBundleSearchRequest.json",
        "useCase": "search",
        "endpoint": "/search/submit",
    },
}

WORKFLOW_FIXTURES: Dict[str, List[str]] = {
    workflow: [details["fixture"]]
    for workflow, details in WORKFLOW_API_DETAILS.items()
}


def list_workflows() -> List[str]:
    return sorted(WORKFLOW_FIXTURES)


def get_api_details(workflow: str) -> dict:
    if workflow not in WORKFLOW_API_DETAILS:
        raise KeyError(f"Unsupported workflow: {workflow}")
    return dict(WORKFLOW_API_DETAILS[workflow])


def get_fixture_path(workflow: str) -> pathlib.Path:
    if workflow not in WORKFLOW_FIXTURES:
        raise KeyError(f"Unsupported workflow: {workflow}")
    fixture_name = WORKFLOW_FIXTURES[workflow][0]
    path = FIXTURES_DIR / fixture_name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path


def load_fixture(workflow: str) -> dict:
    return json.loads(get_fixture_path(workflow).read_text(encoding="utf-8"))


def build_send_payload(workflow: str, hospitalId: str, recipientCode: str, workflowId: str, **optional_fields: str) -> dict:
    details = get_api_details(workflow)
    payload = {
        "hospitalId": hospitalId,
        "useCase": details["useCase"],
        "endpoint": details["endpoint"],
        "workflowId": workflowId,
        "recipientCode": recipientCode,
        "fhirBundle": load_fixture(workflow),
    }
    payload.update({key: value for key, value in optional_fields.items() if value})
    return payload


def describe_workflow(workflow: str) -> dict:
    fixture = load_fixture(workflow)
    details = get_api_details(workflow)
    return {
        "workflow": workflow,
        "fixture": get_fixture_path(workflow).name,
        "useCase": details["useCase"],
        "endpoint": details["endpoint"],
        "resourceType": fixture.get("resourceType"),
        "id": fixture.get("id"),
        "entry_count": len(fixture.get("entry", [])),
    }


def print_summary() -> None:
    for workflow in list_workflows():
        info = describe_workflow(workflow)
        print(
            f"- {workflow}: {info['fixture']} | useCase={info['useCase']} | "
            f"endpoint={info['endpoint']} | resourceType={info['resourceType']} | id={info['id']}"
        )


if __name__ == "__main__":
    print_summary()
