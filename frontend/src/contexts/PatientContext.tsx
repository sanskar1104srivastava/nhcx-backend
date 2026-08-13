import { createContext, useContext, useMemo, useState, ReactNode } from 'react';

export interface CodeItem {
  code: string;
  display: string;
}

export interface LineItem {
  code: string;
  display: string;
  unitPrice: number;
  net: number;
}

export interface DocFile {
  name: string;
  previewUrl: string;
  mimeType: string;
  size: number;
}

export interface PatientRegistration {
  id: string;
  fullName: string;
  gender: string;
  dob: string;
  mobile: string;
  aadhaarNumber: string;
  abhaNumber: string;
  patientPhoto: DocFile | null;
  doctorName: string;
  doctorLicense: string;
  prescription: DocFile | null;
  generalFindings: string;
  familyHistoryDiabetes: string;
  familyHistoryHypertension: string;
  familyHistoryHeartDisease: string;
  familyHistoryStroke: string;
  personalHistoryDiet: string;
  personalHistoryKnownAllergies: string;
  personalHistoryHabitsAddictions: string;
  personalHistoryNutrition: string;
  personalHistoryAppetite: string;
  personalHistoryBowels: string;
  hospitalName: string;
  hospitalRegNumber: string;
  hospitalPhone: string;
  hospitalEmail: string;
  insurerName: string;
  insurerRegNumber: string;
  insurerPhone: string;
  insurerEmail: string;
  policyNumber: string;
  subscriberId: string;
  relationship: string;
  policyValidUntil: string;
  diagnoses: CodeItem[];
  procedures: CodeItem[];
  lineItems: LineItem[];
  documents: DocFile[];
}

interface PatientState {
  patients: PatientRegistration[];
  addPatient: (p: PatientRegistration) => void;
  updatePatient: (p: PatientRegistration) => void;
  removePatient: (id: string) => void;
}

const PatientCtx = createContext<PatientState | null>(null);

export function PatientProvider({ children }: { children: ReactNode }) {
  const [patients, setPatients] = useState<PatientRegistration[]>([]);

  const addPatient = (p: PatientRegistration) => setPatients((prev) => [...prev, p]);
  const updatePatient = (p: PatientRegistration) =>
    setPatients((prev) => prev.map((x) => (x.id === p.id ? p : x)));
  const removePatient = (id: string) => setPatients((prev) => prev.filter((x) => x.id !== id));

  const value = useMemo(() => ({ patients, addPatient, updatePatient, removePatient }), [patients]);
  return <PatientCtx.Provider value={value}>{children}</PatientCtx.Provider>;
}

export function usePatients(): PatientState {
  const ctx = useContext(PatientCtx);
  if (!ctx) throw new Error('usePatients must be used inside <PatientProvider>');
  return ctx;
}
