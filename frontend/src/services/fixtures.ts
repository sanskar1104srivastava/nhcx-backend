const FIXTURE_MODULES: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
  insuranceplan: () => import('../../fixtures/taskBundleInsurancePlanRequest-dummyPayer.json'),
  coverageeligibility: () => import('../../fixtures/coverageEligibilityRequestBundle-dummyPayer.json'),
  preauth: () => import('../../fixtures/claimBundlePreauth-dummyPayer.json'),
  predetermination: () => import('../../fixtures/claimBundlePredetermination-dummyPayer.json'),
  claim: () => import('../../fixtures/claimBundleClaim-dummyPayer.json'),
  communication: () => import('../../fixtures/taskBundleCommunicationResponse-dummyPayer.json'),
  paymentnotice: () => import('../../fixtures/taskBundlePaymentNoticeResponse.json'),
  task: () => import('../../fixtures/taskBundleReprocessRequest.json'),
  search: () => import('../../fixtures/taskBundleSearchRequest.json'),
};

export interface UseCaseConfig {
  label: string;
  endpoint: string;
  workflowId: string;
}

export const USE_CASES: Record<string, UseCaseConfig> = {
  coverageeligibility: { label: 'Coverage Eligibility', endpoint: '/coverageeligibility/check', workflowId: '12' },
  preauth: { label: 'Preauthorization', endpoint: '/preauth/submit', workflowId: '12' },
  claim: { label: 'Claim', endpoint: '/claim/submit', workflowId: '15' },
  predetermination: { label: 'Predetermination', endpoint: '/predetermination/submit', workflowId: '12' },
  insuranceplan: { label: 'Insurance Plan', endpoint: '/insuranceplan/request', workflowId: '2' },
  communication: { label: 'Communication', endpoint: '/communication/on_request', workflowId: '24' },
  paymentnotice: { label: 'Payment Notice', endpoint: '/paymentnotice/on_request', workflowId: '30' },
  task: { label: 'Reprocess / Task', endpoint: '/task/submit', workflowId: '121' },
  search: { label: 'Search', endpoint: '/search/submit', workflowId: '17' },
};

export async function loadFixture(useCase: string): Promise<Record<string, unknown> | null> {
  const loader = FIXTURE_MODULES[useCase];
  if (!loader) return null;
  const mod = await loader();
  return mod.default;
}
