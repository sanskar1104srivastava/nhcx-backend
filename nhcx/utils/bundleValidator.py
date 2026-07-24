"""Structural validation before any outbound bundle leaves us (§7) — "nothing leaves unvalidated".
Cheap, self-contained checks only; full FHIR profile conformance needs the nrces.in IG validator
(§7's CI recommendation), which is a separate, heavier tool this doesn't replace.
"""
from nhcx.constants import BUNDLE_TYPE_COLLECTION, URN_UUID_PREFIX


class BundleValidationError(ValueError):
    pass


def validateBundle(bundle: dict) -> None:
    if bundle.get("resourceType") != "Bundle":
        raise BundleValidationError("resourceType must be 'Bundle'")
    if bundle.get("type") != BUNDLE_TYPE_COLLECTION:
        raise BundleValidationError(f"Bundle.type must be '{BUNDLE_TYPE_COLLECTION}' for claims workflows")

    entries = bundle.get("entry", [])
    if not entries:
        raise BundleValidationError("Bundle.entry must not be empty")

    fullUrls = [e.get("fullUrl") for e in entries]
    if any(not u for u in fullUrls):
        raise BundleValidationError("every entry needs a fullUrl")
    if any(not u.startswith(URN_UUID_PREFIX) for u in fullUrls):
        raise BundleValidationError(f"every fullUrl must start with '{URN_UUID_PREFIX}'")
    if len(fullUrls) != len(set(fullUrls)):
        raise BundleValidationError("duplicate fullUrl in bundle — every entry must be unique")

    resourceTypes = {e["resource"]["resourceType"] for e in entries if "resource" in e}
    if "Claim" in resourceTypes:
        _validateClaimBundle(entries, resourceTypes)


def _validateClaimBundle(entries: list[dict], resourceTypes: set[str]) -> None:
    for required in ("Patient", "Coverage", "Organization"):
        if required not in resourceTypes:
            raise BundleValidationError(f"ClaimBundle with a Claim resource also requires {required} by reference")

    for entry in entries:
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Claim":
            continue
        items = resource.get("item", [])
        if not items:
            continue
        # item.net (when present) is the authoritative line total — real bundles routinely
        # omit quantity when net is already given directly, so unitPrice * quantity alone
        # would wrongly reject them (confirmed against the official nrces.in example).
        computedTotal = sum(
            i["net"]["value"] if i.get("net", {}).get("value") is not None
            else (i.get("unitPrice", {}).get("value", 0) or 0) * (i.get("quantity", {}).get("value", 1) or 1)
            for i in items
        )
        statedTotal = resource.get("total", {}).get("value")
        if statedTotal is not None and round(computedTotal, 2) != round(statedTotal, 2):
            raise BundleValidationError(
                f"Claim.total ({statedTotal}) doesn't match sum(item.net or unitPrice * quantity) ({computedTotal}) "
                "— this is exactly the class of mismatch that gets rejected payer-side"
            )
