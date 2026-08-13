import { PatientRegistration, CodeItem } from '../contexts/PatientContext';

function uuid() {
  return crypto.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function urnUuid(id: string) {
  return `urn:uuid:${id}`;
}

export function buildCoverageEligibilityBundle(p: PatientRegistration) {
  const patientId = uuid();
  const practitionerId = uuid();
  const providerOrgId = uuid();
  const insurerOrgId = uuid();
  const locationId = uuid();
  const coverageId = uuid();
  const requestId = uuid();

  return {
    resourceType: 'Bundle',
    id: `CoverageEligibilityRequestBundle-${requestId}`,
    meta: {
      profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/CoverageEligibilityRequestBundle'],
    },
    identifier: { value: requestId },
    type: 'collection',
    timestamp: new Date().toISOString(),
    entry: [
      {
        fullUrl: urnUuid(requestId),
        resource: {
          resourceType: 'CoverageEligibilityRequest',
          id: requestId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/CoverageEligibilityRequest'] },
          status: 'active',
          priority: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/processpriority', code: 'normal', display: 'Normal' }] },
          purpose: ['validation'],
          patient: { reference: urnUuid(patientId), display: p.fullName },
          created: new Date().toISOString(),
          enterer: { reference: urnUuid(practitionerId), display: p.doctorName },
          provider: { reference: urnUuid(providerOrgId), display: p.hospitalName },
          insurer: { reference: urnUuid(insurerOrgId), display: p.insurerName },
          facility: { reference: urnUuid(locationId), display: 'Main Facility' },
          insurance: [{ focal: true, coverage: { reference: urnUuid(coverageId) } }],
        },
      },
      {
        fullUrl: urnUuid(patientId),
        resource: {
          resourceType: 'Patient',
          id: patientId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient'] },
          identifier: [
            ...(p.abhaNumber ? [{ type: { coding: [{ system: 'https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code', code: 'ABHA' }] }, value: p.abhaNumber }] : []),
            ...(p.aadhaarNumber ? [{ type: { coding: [{ system: 'https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code', code: 'ADN' }] }, system: 'https://uidai.gov.in/', value: p.aadhaarNumber }] : []),
          ],
          name: [{ text: p.fullName }],
          telecom: p.mobile ? [{ system: 'phone', value: p.mobile, use: 'home' }] : [],
          gender: p.gender || 'male',
          birthDate: p.dob || undefined,
        },
      },
      {
        fullUrl: urnUuid(practitionerId),
        resource: {
          resourceType: 'Practitioner',
          id: practitionerId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Practitioner'] },
          identifier: p.doctorLicense ? [{ type: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v2-0203', code: 'MD', display: 'Medical License number' }] }, system: 'https://doctor.ndhm.gov.in', value: p.doctorLicense }] : [],
          name: [{ text: p.doctorName }],
        },
      },
      {
        fullUrl: urnUuid(insurerOrgId),
        resource: {
          resourceType: 'Organization',
          id: insurerOrgId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization'] },
          identifier: p.insurerRegNumber ? [{ type: { coding: [{ system: 'https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code', code: 'ROHINI' }] }, value: p.insurerRegNumber }] : [],
          type: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/organization-type', code: 'ins', display: 'Insurance Company' }] }],
          name: p.insurerName,
          telecom: [
            ...(p.insurerPhone ? [{ system: 'phone', value: p.insurerPhone, use: 'work' }] : []),
            ...(p.insurerEmail ? [{ system: 'email', value: p.insurerEmail, use: 'work' }] : []),
          ],
        },
      },
      {
        fullUrl: urnUuid(providerOrgId),
        resource: {
          resourceType: 'Organization',
          id: providerOrgId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization'] },
          identifier: p.hospitalRegNumber ? [{ type: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v2-0203', code: 'PRN' }] }, system: 'https://facility.ndhm.gov.in', value: p.hospitalRegNumber }] : [],
          type: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/organization-type', code: 'prov', display: 'Healthcare Provider' }] }],
          name: p.hospitalName,
          telecom: [
            ...(p.hospitalPhone ? [{ system: 'phone', value: p.hospitalPhone, use: 'work' }] : []),
            ...(p.hospitalEmail ? [{ system: 'email', value: p.hospitalEmail, use: 'work' }] : []),
          ],
        },
      },
      {
        fullUrl: urnUuid(locationId),
        resource: {
          resourceType: 'Location',
          id: locationId,
          status: 'active',
          name: 'Main Facility',
          managingOrganization: { reference: urnUuid(providerOrgId) },
        },
      },
      {
        fullUrl: urnUuid(coverageId),
        resource: {
          resourceType: 'Coverage',
          id: coverageId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Coverage'] },
          status: 'active',
          type: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v3-ActCode', code: 'HIP', display: 'health insurance plan policy' }] },
          subscriber: { reference: urnUuid(patientId) },
          subscriberId: p.subscriberId || p.policyNumber,
          beneficiary: { reference: urnUuid(patientId) },
          relationship: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/subscriber-relationship', code: p.relationship || 'self' }] },
          period: p.policyValidUntil ? { end: p.policyValidUntil } : undefined,
          payor: [{ reference: urnUuid(insurerOrgId) }],
          identifier: p.policyNumber ? [{ system: 'https://nhcx.in/policynumber/', value: p.policyNumber }] : [],
        },
      },
    ],
  };
}

export function buildClaimBundle(p: PatientRegistration, useCase: 'preauthorization' | 'claim' | 'predetermination' = 'preauthorization') {
  const patientId = uuid();
  const practitionerId = uuid();
  const providerOrgId = uuid();
  const insurerOrgId = uuid();
  const coverageId = uuid();
  const claimId = uuid();

  const totalNet = p.lineItems.reduce((sum, it) => sum + (it.net || 0), 0);

  return {
    resourceType: 'Bundle',
    id: `ClaimBundle-${claimId}`,
    meta: {
      profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/ClaimBundle'],
    },
    identifier: { value: claimId },
    type: 'collection',
    timestamp: new Date().toISOString(),
    entry: [
      {
        fullUrl: urnUuid(claimId),
        resource: {
          resourceType: 'Claim',
          id: claimId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Claim'] },
          status: 'active',
          type: { coding: [{ system: 'http://snomed.info/sct', code: '737481003', display: 'Inpatient care management (procedure)' }] },
          use: useCase,
          patient: { reference: urnUuid(patientId), display: p.fullName },
          billablePeriod: { start: new Date().toISOString(), end: new Date(Date.now() + 30 * 86400000).toISOString() },
          created: new Date().toISOString(),
          insurer: { reference: urnUuid(insurerOrgId), display: p.insurerName },
          provider: { reference: urnUuid(providerOrgId), display: p.hospitalName },
          priority: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/processpriority', code: 'normal' }] },
          careTeam: p.doctorName ? [{ sequence: 1, provider: { reference: urnUuid(practitionerId), display: p.doctorName } }] : [],
          diagnosis: p.diagnoses.filter((d) => d.code).map((d, i) => ({
            sequence: i + 1,
            diagnosisCodeableConcept: { coding: [{ system: 'http://hl7.org/fhir/sid/icd-10', code: d.code, display: d.display }] },
          })),
          procedure: p.procedures.filter((pr) => pr.code).map((pr, i) => ({
            sequence: i + 1,
            procedureCodeableConcept: { coding: [{ system: 'http://snomed.info/sct', code: pr.code, display: pr.display }] },
          })),
          insurance: [{ sequence: 1, focal: true, coverage: { reference: urnUuid(coverageId), display: 'Coverage' } }],
          item: p.lineItems.filter((it) => it.code || it.display).map((it, i) => ({
            sequence: i + 1,
            careTeamSequence: [1],
            productOrService: { coding: [{ system: 'http://snomed.info/sct', code: it.code || 'N/A', display: it.display }] },
            unitPrice: { value: it.unitPrice || it.net, currency: 'INR' },
            net: { value: it.net || it.unitPrice, currency: 'INR' },
          })),
          total: totalNet > 0 ? { value: totalNet, currency: 'INR' } : undefined,
        },
      },
      {
        fullUrl: urnUuid(patientId),
        resource: {
          resourceType: 'Patient',
          id: patientId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient'] },
          identifier: [
            ...(p.abhaNumber ? [{ type: { coding: [{ system: 'https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code', code: 'ABHA' }] }, value: p.abhaNumber }] : []),
            ...(p.aadhaarNumber ? [{ type: { coding: [{ system: 'https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code', code: 'ADN' }] }, system: 'https://uidai.gov.in/', value: p.aadhaarNumber }] : []),
          ],
          name: [{ text: p.fullName }],
          telecom: p.mobile ? [{ system: 'phone', value: p.mobile, use: 'home' }] : [],
          gender: p.gender || 'male',
          birthDate: p.dob || undefined,
        },
      },
      {
        fullUrl: urnUuid(insurerOrgId),
        resource: {
          resourceType: 'Organization',
          id: insurerOrgId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization'] },
          identifier: p.insurerRegNumber ? [{ type: { coding: [{ system: 'https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code', code: 'ROHINI' }] }, value: p.insurerRegNumber }] : [],
          type: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/organization-type', code: 'ins' }] }],
          name: p.insurerName,
        },
      },
      {
        fullUrl: urnUuid(providerOrgId),
        resource: {
          resourceType: 'Organization',
          id: providerOrgId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization'] },
          identifier: p.hospitalRegNumber ? [{ type: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v2-0203', code: 'PRN' }] }, system: 'https://facility.ndhm.gov.in', value: p.hospitalRegNumber }] : [],
          type: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/organization-type', code: 'prov' }] }],
          name: p.hospitalName,
        },
      },
      ...(p.doctorName ? [{
        fullUrl: urnUuid(practitionerId),
        resource: {
          resourceType: 'Practitioner',
          id: practitionerId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Practitioner'] },
          identifier: p.doctorLicense ? [{ type: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v2-0203', code: 'MD' }] }, system: 'https://doctor.ndhm.gov.in', value: p.doctorLicense }] : [],
          name: [{ text: p.doctorName }],
        },
      }] : []),
      {
        fullUrl: urnUuid(coverageId),
        resource: {
          resourceType: 'Coverage',
          id: coverageId,
          meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/Coverage'] },
          status: 'active',
          type: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v3-ActCode', code: 'HIP' }] },
          subscriber: { reference: urnUuid(patientId) },
          subscriberId: p.subscriberId || p.policyNumber,
          beneficiary: { reference: urnUuid(patientId) },
          relationship: { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/subscriber-relationship', code: p.relationship || 'self' }] },
          payor: [{ reference: urnUuid(insurerOrgId) }],
          identifier: p.policyNumber ? [{ system: 'https://nhcx.in/policynumber/', value: p.policyNumber }] : [],
        },
      },
    ],
  };
}

export function buildTaskBundle(p: PatientRegistration, taskCode: string, extraInput?: Array<{ type: string; valueString: string }>) {
  const taskId = uuid();
  const providerOrgId = uuid();
  const insurerOrgId = uuid();

  return {
    resourceType: 'Bundle',
    id: `TaskBundle-${taskId}`,
    meta: { profile: ['https://nrces.in/ndhm/fhir/r4/StructureDefinition/TaskBundle'] },
    identifier: { value: taskId },
    type: 'collection',
    timestamp: new Date().toISOString(),
    entry: [
      {
        fullUrl: urnUuid(taskId),
        resource: {
          resourceType: 'Task',
          id: taskId,
          status: 'requested',
          intent: 'order',
          code: { coding: [{ code: taskCode }] },
          focus: extraInput?.[0] ? { identifier: { value: extraInput[0].valueString } } : undefined,
          input: extraInput,
        },
      },
      {
        fullUrl: urnUuid(providerOrgId),
        resource: {
          resourceType: 'Organization',
          id: providerOrgId,
          name: p.hospitalName || 'Provider',
          identifier: p.hospitalRegNumber ? [{ value: p.hospitalRegNumber }] : [],
        },
      },
      {
        fullUrl: urnUuid(insurerOrgId),
        resource: {
          resourceType: 'Organization',
          id: insurerOrgId,
          name: p.insurerName || 'Insurer',
          identifier: p.insurerRegNumber ? [{ value: p.insurerRegNumber }] : [],
        },
      },
    ],
  };
}
