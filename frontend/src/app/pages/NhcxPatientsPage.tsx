import { useState } from 'react';
import {
  Plus, Trash2, Users, FileUp, X, UserPlus, Check,
  FileText, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { Badge } from '../components/ui/badge';
import { cn } from '../components/ui/utils';
import { toast } from 'sonner';
import { usePatients } from '../../contexts/PatientContext';

interface CodeItem {
  code: string;
  display: string;
}

interface LineItem {
  code: string;
  display: string;
  unitPrice: number;
  net: number;
}

interface DocFile {
  name: string;
  previewUrl: string; // data URL for images, '' for non-image files (e.g. PDF)
  mimeType: string;
  size: number; // bytes
}

interface PatientRegistration {
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

const emptyDiagnosis: CodeItem = { code: '', display: '' };
const emptyProcedure: CodeItem = { code: '', display: '' };
const emptyLineItem: LineItem = { code: '', display: '', unitPrice: 0, net: 0 };

const STEPS = [
  { label: 'Patient Details & History', description: 'Identity, doctor & medical history' },
  { label: 'Investigation of Insurance', description: 'Hospital, insurer & policy' },
  { label: 'Diagnosis Details', description: 'Diagnosis, billing & uploads' },
] as const;

function formatSize(bytes: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Reads a File into a DocFile — images get a data-URL preview, other types
// (e.g. PDFs) just keep the file name so we can still show/list them.
function readDocFile(file: File): Promise<DocFile> {
  return new Promise((resolve) => {
    if (!file.type.startsWith('image/')) {
      resolve({
        name: file.name, previewUrl: '', mimeType: file.type, size: file.size,
      });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve({
      name: file.name, previewUrl: reader.result as string, mimeType: file.type, size: file.size,
    });
    reader.onerror = () => resolve({
      name: file.name, previewUrl: '', mimeType: file.type, size: file.size,
    });
    reader.readAsDataURL(file);
  });
}

// ---- Timeline / stepper -----------------------------------------------

function StepTimeline({
  current, furthestVisited, onStepClick,
}: { current: number; furthestVisited: number; onStepClick: (i: number) => void }) {
  return (
    <div className="w-full py-2">
      <div className="flex items-start">
        {STEPS.map((step, i) => {
          const isCompleted = i < current;
          const isCurrent = i === current;
          const isClickable = i <= furthestVisited;
          return (
            <div key={step.label} className={cn('flex items-center', i < STEPS.length - 1 && 'flex-1')}>
              <div className="flex flex-col items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => isClickable && onStepClick(i)}
                  className={cn(
                    'flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors',
                    isCompleted && 'border-emerald-500 bg-emerald-500 text-white',
                    isCurrent && 'border-cyan-600 bg-cyan-600 text-white shadow-[0_0_0_4px_rgba(8,145,178,0.15)]',
                    !isCompleted && !isCurrent && 'border-gray-300 bg-white text-gray-400 dark:border-gray-600 dark:bg-gray-900',
                    isClickable && !isCurrent && 'cursor-pointer hover:border-cyan-500',
                    !isClickable && 'cursor-not-allowed',
                  )}
                >
                  {isCompleted ? <Check className="h-4 w-4" /> : i + 1}
                </button>
                <div className="text-center max-w-[110px] sm:max-w-[140px]">
                  <p className={cn(
                    'text-xs font-medium leading-tight',
                    isCurrent ? 'text-cyan-700 dark:text-cyan-400' : isCompleted ? 'text-emerald-600' : 'text-gray-400',
                  )}
                  >
                    {step.label}
                  </p>
                  <p className="hidden sm:block text-[11px] text-gray-400 leading-tight mt-0.5">{step.description}</p>
                </div>
              </div>
              {i < STEPS.length - 1 && (
                <div className={cn('h-0.5 flex-1 mx-1 sm:mx-2 mt-[18px] rounded', isCompleted ? 'bg-emerald-500' : 'bg-gray-200 dark:bg-gray-700')} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---- Document preview tiles --------------------------------------------

function SingleDocPreview({
  label, doc, onChange, onRemove, accept = 'image/*,application/pdf',
}: {
  label: string;
  doc: DocFile | null;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onRemove: () => void;
  accept?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {doc ? (
        <div className="flex items-center gap-3 rounded-lg border bg-gray-50 dark:bg-gray-900/40 p-2.5">
          {doc.previewUrl ? (
            <img src={doc.previewUrl} alt={doc.name} className="h-16 w-16 shrink-0 rounded-md object-cover border" />
          ) : (
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md border bg-red-50 dark:bg-red-950/30">
              <FileText className="h-7 w-7 text-red-500" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-gray-800 dark:text-gray-100">{doc.name}</p>
            <p className="text-xs text-gray-400">
              {doc.previewUrl ? 'Image' : 'PDF'}{doc.size ? ` · ${formatSize(doc.size)}` : ''}
            </p>
            <Badge variant="outline" className="mt-1 gap-1 border-emerald-300 text-emerald-600">
              <Check className="h-3 w-3" /> Uploaded
            </Badge>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="shrink-0 rounded-full p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
            aria-label={`Remove ${label}`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed p-3 text-sm text-gray-500 hover:border-cyan-400 hover:bg-cyan-50/40 dark:hover:bg-cyan-950/10">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-gray-100 dark:bg-gray-800">
            <FileUp className="h-4.5 w-4.5 text-gray-400" />
          </div>
          <span>Click to upload {label.toLowerCase()}</span>
          <input type="file" accept={accept} onChange={onChange} className="hidden" />
        </label>
      )}
    </div>
  );
}

function MultiDocGallery({
  documents, onAdd, onRemove,
}: { documents: DocFile[]; onAdd: (e: React.ChangeEvent<HTMLInputElement>) => void; onRemove: (i: number) => void }) {
  return (
    <div className="space-y-2 pt-2 border-t">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Additional Documents</h4>
        <Badge variant="secondary">{documents.length} uploaded</Badge>
      </div>
      <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed p-3 text-sm text-gray-500 hover:border-cyan-400 hover:bg-cyan-50/40 dark:hover:bg-cyan-950/10 w-fit">
        <FileUp className="h-4 w-4 text-gray-400" />
        Upload photos or PDFs
        <input type="file" accept="image/*,application/pdf" multiple onChange={onAdd} className="hidden" />
      </label>

      {documents.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 pt-1">
          {documents.map((doc, i) => (
            <div key={i} className="group relative rounded-lg border bg-gray-50 dark:bg-gray-900/40 p-2">
              <button
                type="button"
                onClick={() => onRemove(i)}
                className="absolute -right-1.5 -top-1.5 z-10 rounded-full bg-white border shadow p-1 text-gray-400 opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity"
                aria-label={`Remove ${doc.name}`}
              >
                <X className="h-3 w-3" />
              </button>
              {doc.previewUrl ? (
                <img src={doc.previewUrl} alt={doc.name} className="h-24 w-full rounded-md object-cover border" />
              ) : (
                <div className="flex h-24 w-full flex-col items-center justify-center gap-1 rounded-md border bg-red-50 dark:bg-red-950/30">
                  <FileText className="h-7 w-7 text-red-500" />
                  <span className="text-[10px] font-medium text-red-500">PDF</span>
                </div>
              )}
              <p className="mt-1.5 truncate text-xs font-medium text-gray-700 dark:text-gray-200">{doc.name}</p>
              <p className="text-[11px] text-gray-400">{formatSize(doc.size)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function NhcxPatientsPage() {
  // Step navigation
  const [currentStep, setCurrentStep] = useState(0);
  const [furthestVisited, setFurthestVisited] = useState(0);

  // Patient identity
  const [fullName, setFullName] = useState('');
  const [gender, setGender] = useState('male');
  const [dob, setDob] = useState('');
  const [mobile, setMobile] = useState('');
  const [aadhaarNumber, setAadhaarNumber] = useState('');
  const [abhaNumber, setAbhaNumber] = useState('');
  const [patientPhoto, setPatientPhoto] = useState<DocFile | null>(null);

  // Treating doctor + prescription
  const [doctorName, setDoctorName] = useState('');
  const [doctorLicense, setDoctorLicense] = useState('');
  const [prescription, setPrescription] = useState<DocFile | null>(null);

  // Medical history
  const [generalFindings, setGeneralFindings] = useState('');
  const [familyHistoryDiabetes, setFamilyHistoryDiabetes] = useState('');
  const [familyHistoryHypertension, setFamilyHistoryHypertension] = useState('');
  const [familyHistoryHeartDisease, setFamilyHistoryHeartDisease] = useState('');
  const [familyHistoryStroke, setFamilyHistoryStroke] = useState('');
  const [personalHistoryDiet, setPersonalHistoryDiet] = useState('');
  const [personalHistoryKnownAllergies, setPersonalHistoryKnownAllergies] = useState('');
  const [personalHistoryHabitsAddictions, setPersonalHistoryHabitsAddictions] = useState('');
  const [personalHistoryNutrition, setPersonalHistoryNutrition] = useState('');
  const [personalHistoryAppetite, setPersonalHistoryAppetite] = useState('');
  const [personalHistoryBowels, setPersonalHistoryBowels] = useState('');

  // Hospital (provider)
  const [hospitalName, setHospitalName] = useState('');
  const [hospitalRegNumber, setHospitalRegNumber] = useState('');
  const [hospitalPhone, setHospitalPhone] = useState('');
  const [hospitalEmail, setHospitalEmail] = useState('');

  // Insurer
  const [insurerName, setInsurerName] = useState('');
  const [insurerRegNumber, setInsurerRegNumber] = useState('');
  const [insurerPhone, setInsurerPhone] = useState('');
  const [insurerEmail, setInsurerEmail] = useState('');

  // Policy / coverage
  const [policyNumber, setPolicyNumber] = useState('');
  const [subscriberId, setSubscriberId] = useState('');
  const [relationship, setRelationship] = useState('self');
  const [policyValidUntil, setPolicyValidUntil] = useState('');

  // Clinical + billing
  const [diagnoses, setDiagnoses] = useState<CodeItem[]>([emptyDiagnosis]);
  const [procedures, setProcedures] = useState<CodeItem[]>([emptyProcedure]);
  const [lineItems, setLineItems] = useState<LineItem[]>([emptyLineItem]);

  // Other supporting documents
  const [documents, setDocuments] = useState<DocFile[]>([]);

  // Saved patients (shared across pages)
  const { patients, addPatient, updatePatient } = usePatients();
  // Non-null while an existing patient record is being edited/added to
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const total = lineItems.reduce((sum, it) => sum + (it.net || 0), 0);

  // Looks for an already-registered patient with the same Aadhaar or ABHA
  // number (excluding whichever record is currently being edited).
  const findExistingPatient = (aadhaar: string, abha: string) => {
    const a = aadhaar.trim();
    const b = abha.trim();
    if (!a && !b) return undefined;
    return patients.find((p) => p.id !== editingId && (
      (a && p.aadhaarNumber.trim() === a) || (b && p.abhaNumber.trim() === b)
    ));
  };

  const duplicateMatch = editingId ? undefined : findExistingPatient(aadhaarNumber, abhaNumber);


  const handlePatientPhotoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setPatientPhoto(await readDocFile(file));
  };

  const handlePrescriptionChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setPrescription(await readDocFile(file));
  };

  const handleDocumentsChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    const read = await Promise.all(files.map(readDocFile));
    setDocuments((prev) => [...prev, ...read]);
    e.target.value = '';
  };

  const removeDocument = (index: number) => {
    setDocuments((prev) => prev.filter((_, i) => i !== index));
  };

  const resetForm = () => {
    setFullName(''); setGender('male'); setDob(''); setMobile('');
    setAadhaarNumber(''); setAbhaNumber(''); setPatientPhoto(null);
    setDoctorName(''); setDoctorLicense(''); setPrescription(null);
    setGeneralFindings('');
    setFamilyHistoryDiabetes(''); setFamilyHistoryHypertension(''); setFamilyHistoryHeartDisease(''); setFamilyHistoryStroke('');
    setPersonalHistoryDiet(''); setPersonalHistoryKnownAllergies(''); setPersonalHistoryHabitsAddictions('');
    setPersonalHistoryNutrition(''); setPersonalHistoryAppetite(''); setPersonalHistoryBowels('');
    setHospitalName(''); setHospitalRegNumber(''); setHospitalPhone(''); setHospitalEmail('');
    setInsurerName(''); setInsurerRegNumber(''); setInsurerPhone(''); setInsurerEmail('');
    setPolicyNumber(''); setSubscriberId(''); setRelationship('self'); setPolicyValidUntil('');
    setDiagnoses([emptyDiagnosis]); setProcedures([emptyProcedure]); setLineItems([emptyLineItem]);
    setDocuments([]);
    setCurrentStep(0);
    setFurthestVisited(0);
    setEditingId(null);
  };

  // Loads a saved patient's full data into the form so it can be edited or
  // added to, instead of creating a duplicate record.
  const loadPatientForEdit = (p: PatientRegistration) => {
    setFullName(p.fullName); setGender(p.gender); setDob(p.dob); setMobile(p.mobile);
    setAadhaarNumber(p.aadhaarNumber); setAbhaNumber(p.abhaNumber); setPatientPhoto(p.patientPhoto);
    setDoctorName(p.doctorName); setDoctorLicense(p.doctorLicense); setPrescription(p.prescription);
    setGeneralFindings(p.generalFindings);
    setFamilyHistoryDiabetes(p.familyHistoryDiabetes); setFamilyHistoryHypertension(p.familyHistoryHypertension);
    setFamilyHistoryHeartDisease(p.familyHistoryHeartDisease); setFamilyHistoryStroke(p.familyHistoryStroke);
    setPersonalHistoryDiet(p.personalHistoryDiet); setPersonalHistoryKnownAllergies(p.personalHistoryKnownAllergies);
    setPersonalHistoryHabitsAddictions(p.personalHistoryHabitsAddictions); setPersonalHistoryNutrition(p.personalHistoryNutrition);
    setPersonalHistoryAppetite(p.personalHistoryAppetite); setPersonalHistoryBowels(p.personalHistoryBowels);
    setHospitalName(p.hospitalName); setHospitalRegNumber(p.hospitalRegNumber); setHospitalPhone(p.hospitalPhone); setHospitalEmail(p.hospitalEmail);
    setInsurerName(p.insurerName); setInsurerRegNumber(p.insurerRegNumber); setInsurerPhone(p.insurerPhone); setInsurerEmail(p.insurerEmail);
    setPolicyNumber(p.policyNumber); setSubscriberId(p.subscriberId); setRelationship(p.relationship); setPolicyValidUntil(p.policyValidUntil);
    setDiagnoses(p.diagnoses.length ? p.diagnoses : [emptyDiagnosis]);
    setProcedures(p.procedures.length ? p.procedures : [emptyProcedure]);
    setLineItems(p.lineItems.length ? p.lineItems : [emptyLineItem]);
    setDocuments(p.documents);
    setEditingId(p.id);
    setShowForm(true);
    setCurrentStep(0);
    setFurthestVisited(STEPS.length - 1);
    toast.info(`Editing ${p.fullName} — update details or add more info, then save`);
  };


  const goToStep = (i: number) => setCurrentStep(i);

  const handleNext = () => {
    if (currentStep === 0) {
      if (!fullName.trim()) {
        toast.error('Full name is required');
        return;
      }
      if (!aadhaarNumber.trim() && !abhaNumber.trim()) {
        toast.error('Enter Aadhaar Number or ABHA Number');
        return;
      }
      if (!mobile.trim()) {
        toast.error('Mobile number is required');
        return;
      }
      if (duplicateMatch) {
        toast.error('This patient already exists — edit their record instead of creating a new one');
        return;
      }
    }
    if (currentStep === 1) {
      if (!hospitalName.trim()) {
        toast.error('Hospital (provider) name is required');
        return;
      }
    }
    const next = Math.min(currentStep + 1, STEPS.length - 1);
    setCurrentStep(next);
    setFurthestVisited((prev) => Math.max(prev, next));
  };

  const handleBack = () => setCurrentStep((prev) => Math.max(prev - 1, 0));

  const handleSavePatient = () => {
    if (!fullName.trim()) {
      toast.error('Full name is required');
      setCurrentStep(0);
      return;
    }
    if (!aadhaarNumber.trim() && !abhaNumber.trim()) {
      toast.error('Enter Aadhaar Number or ABHA Number');
      setCurrentStep(0);
      return;
    }
    if (!mobile.trim()) {
      toast.error('Mobile number is required');
      setCurrentStep(0);
      return;
    }
    if (!hospitalName.trim()) {
      toast.error('Hospital (provider) name is required');
      setCurrentStep(1);
      return;
    }
    if (duplicateMatch) {
      toast.error('This patient already exists — edit their record instead of creating a new one');
      setCurrentStep(0);
      return;
    }

    const cleanDiagnoses = diagnoses.filter((d) => d.code.trim() || d.display.trim());
    const cleanProcedures = procedures.filter((p) => p.code.trim() || p.display.trim());
    const cleanLineItems = lineItems.filter((it) => it.code.trim() || it.display.trim());

    const record: PatientRegistration = {
      id: editingId ?? `${Date.now()}`,
      fullName: fullName.trim(),
      gender,
      dob,
      mobile,
      aadhaarNumber,
      abhaNumber,
      patientPhoto,
      doctorName,
      doctorLicense,
      prescription,
      generalFindings,
      familyHistoryDiabetes,
      familyHistoryHypertension,
      familyHistoryHeartDisease,
      familyHistoryStroke,
      personalHistoryDiet,
      personalHistoryKnownAllergies,
      personalHistoryHabitsAddictions,
      personalHistoryNutrition,
      personalHistoryAppetite,
      personalHistoryBowels,
      hospitalName,
      hospitalRegNumber,
      hospitalPhone,
      hospitalEmail,
      insurerName,
      insurerRegNumber,
      insurerPhone,
      insurerEmail,
      policyNumber,
      subscriberId,
      relationship,
      policyValidUntil,
      diagnoses: cleanDiagnoses,
      procedures: cleanProcedures,
      lineItems: cleanLineItems,
      documents,
    };

    if (editingId) {
      updatePatient(record);
    } else {
      addPatient(record);
    }
    toast.success(editingId ? 'Patient updated' : 'Patient registered');
    resetForm();
    setShowForm(false);
  };

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">Patients</h1>
          <p className="text-gray-500 dark:text-gray-400">
            {showForm
              ? (editingId ? 'Edit patient details' : 'Register a new patient')
              : `${patients.length} registered patient${patients.length !== 1 ? 's' : ''} — select one for NHCX claims`}
          </p>
        </div>
        {!showForm && (
          <Button onClick={() => { setEditingId(null); setShowForm(true); resetForm(); }} className="gap-2">
            <UserPlus className="h-4 w-4" /> Register New Patient
          </Button>
        )}
        {showForm && (
          <Button variant="outline" onClick={() => { setShowForm(false); setEditingId(null); }}>
            Back to List
          </Button>
        )}
      </div>

      {showForm ? (
        <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle>{editingId ? 'Edit Patient' : 'Patient Registration'}</CardTitle>
              <CardDescription>
                {editingId
                  ? 'Update this patient\'s details or add new documents, diagnosis & billing info'
                  : 'Fields required to raise preauth, claim, or coverage-eligibility requests for this patient'}
              </CardDescription>
            </div>
            {editingId && (
              <Button type="button" variant="outline" size="sm" onClick={resetForm}>
                Cancel edit / New patient
              </Button>
            )}
          </div>
          <StepTimeline current={currentStep} furthestVisited={furthestVisited} onStepClick={goToStep} />
        </CardHeader>
        <CardContent className="space-y-6">

          {/* Step 1: Patient & Doctor */}
          {currentStep === 0 && (
            <div className="space-y-6">
              {duplicateMatch && (
                <div className="flex items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950/20 p-3">
                  <div className="flex items-center gap-2 text-sm text-amber-800 dark:text-amber-300">
                    <Users className="h-4 w-4 shrink-0" />
                    <span>
                      <span className="font-semibold">{duplicateMatch.fullName}</span> is already registered with this Aadhaar/ABHA number.
                      Editing is required instead of creating a duplicate.
                    </span>
                  </div>
                  <Button type="button" size="sm" className="shrink-0" onClick={() => loadPatientForEdit(duplicateMatch)}>
                    Edit this patient
                  </Button>
                </div>
              )}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Patient</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Full Name</Label>
                    <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Patient name" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Gender</Label>
                    <Select value={gender} onValueChange={setGender}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="male">Male</SelectItem>
                        <SelectItem value="female">Female</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Date of Birth</Label>
                    <Input type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Mobile Number</Label>
                    <Input value={mobile} onChange={(e) => setMobile(e.target.value)} placeholder="9876543210" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Aadhaar Number</Label>
                    <Input value={aadhaarNumber} onChange={(e) => setAadhaarNumber(e.target.value)} placeholder="XXXX-XXXX-XXXX" className="font-mono" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>ABHA Number</Label>
                    <Input value={abhaNumber} onChange={(e) => setAbhaNumber(e.target.value)} placeholder="14-digit ABHA number" className="font-mono" />
                  </div>
                  <div className="col-span-2">
                    <SingleDocPreview
                      label="Patient Photograph"
                      doc={patientPhoto}
                      onChange={handlePatientPhotoChange}
                      onRemove={() => setPatientPhoto(null)}
                      accept="image/*"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Treating Doctor</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Doctor Name</Label>
                    <Input value={doctorName} onChange={(e) => setDoctorName(e.target.value)} placeholder="Dr. Name" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Medical License Number</Label>
                    <Input value={doctorLicense} onChange={(e) => setDoctorLicense(e.target.value)} className="font-mono" />
                  </div>
                  <div className="col-span-2">
                    <SingleDocPreview
                      label="Doctor's Prescription"
                      doc={prescription}
                      onChange={handlePrescriptionChange}
                      onRemove={() => setPrescription(null)}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">General Findings</h4>
                <div className="space-y-1.5">
                  <Label>Findings</Label>
                  <Input value={generalFindings} onChange={(e) => setGeneralFindings(e.target.value)} placeholder="e.g. None" />
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Family History</h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="space-y-1.5">
                    <Label>Diabetes</Label>
                    <Input value={familyHistoryDiabetes} onChange={(e) => setFamilyHistoryDiabetes(e.target.value)} placeholder="None" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Hypertension</Label>
                    <Input value={familyHistoryHypertension} onChange={(e) => setFamilyHistoryHypertension(e.target.value)} placeholder="None" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Heart Disease</Label>
                    <Input value={familyHistoryHeartDisease} onChange={(e) => setFamilyHistoryHeartDisease(e.target.value)} placeholder="None" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Stroke</Label>
                    <Input value={familyHistoryStroke} onChange={(e) => setFamilyHistoryStroke(e.target.value)} placeholder="None" />
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Personal History</h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="space-y-1.5">
                    <Label>Diet</Label>
                    <Input value={personalHistoryDiet} onChange={(e) => setPersonalHistoryDiet(e.target.value)} placeholder="Normal" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Known Allergies</Label>
                    <Input value={personalHistoryKnownAllergies} onChange={(e) => setPersonalHistoryKnownAllergies(e.target.value)} placeholder="None" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Habits / Addictions</Label>
                    <Input value={personalHistoryHabitsAddictions} onChange={(e) => setPersonalHistoryHabitsAddictions(e.target.value)} placeholder="None" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Nutrition</Label>
                    <Input value={personalHistoryNutrition} onChange={(e) => setPersonalHistoryNutrition(e.target.value)} placeholder="Normal" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Appetite</Label>
                    <Input value={personalHistoryAppetite} onChange={(e) => setPersonalHistoryAppetite(e.target.value)} placeholder="Normal" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Bowels</Label>
                    <Input value={personalHistoryBowels} onChange={(e) => setPersonalHistoryBowels(e.target.value)} placeholder="Normal" />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Hospital, Insurer & Policy */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Hospital (Provider)</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5 col-span-2">
                    <Label>Name</Label>
                    <Input value={hospitalName} onChange={(e) => setHospitalName(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>ROHINI / Provider Number</Label>
                    <Input value={hospitalRegNumber} onChange={(e) => setHospitalRegNumber(e.target.value)} className="font-mono" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Phone</Label>
                    <Input value={hospitalPhone} onChange={(e) => setHospitalPhone(e.target.value)} />
                  </div>
                  <div className="space-y-1.5 col-span-2">
                    <Label>Email</Label>
                    <Input type="email" value={hospitalEmail} onChange={(e) => setHospitalEmail(e.target.value)} />
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Insurer</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5 col-span-2">
                    <Label>Name</Label>
                    <Input value={insurerName} onChange={(e) => setInsurerName(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>ROHINI / Provider Number</Label>
                    <Input value={insurerRegNumber} onChange={(e) => setInsurerRegNumber(e.target.value)} className="font-mono" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Phone</Label>
                    <Input value={insurerPhone} onChange={(e) => setInsurerPhone(e.target.value)} />
                  </div>
                  <div className="space-y-1.5 col-span-2">
                    <Label>Email</Label>
                    <Input type="email" value={insurerEmail} onChange={(e) => setInsurerEmail(e.target.value)} />
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2 border-t">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Policy / Coverage</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Policy Number</Label>
                    <Input value={policyNumber} onChange={(e) => setPolicyNumber(e.target.value)} className="font-mono" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Subscriber ID</Label>
                    <Input value={subscriberId} onChange={(e) => setSubscriberId(e.target.value)} className="font-mono" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Relationship to Subscriber</Label>
                    <Select value={relationship} onValueChange={setRelationship}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="self">Self</SelectItem>
                        <SelectItem value="spouse">Spouse</SelectItem>
                        <SelectItem value="child">Child</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Policy Valid Until</Label>
                    <Input type="date" value={policyValidUntil} onChange={(e) => setPolicyValidUntil(e.target.value)} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Clinical & Documents */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Diagnosis (ICD-10)</h4>
                {diagnoses.map((d, i) => (
                  <div key={i} className="flex gap-2 items-start">
                    <Input
                      value={d.code}
                      onChange={(e) => setDiagnoses(diagnoses.map((x, j) => (j === i ? { ...x, code: e.target.value } : x)))}
                      placeholder="ICD-10 code, e.g. I46.9"
                      className="w-40 font-mono"
                    />
                    <Input
                      value={d.display}
                      onChange={(e) => setDiagnoses(diagnoses.map((x, j) => (j === i ? { ...x, display: e.target.value } : x)))}
                      placeholder="Description, e.g. Cardiac arrest"
                      className="flex-1"
                    />
                    <Button type="button" variant="outline" size="icon" onClick={() => setDiagnoses(diagnoses.filter((_, j) => j !== i))} disabled={diagnoses.length === 1}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                ))}
                <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => setDiagnoses([...diagnoses, { ...emptyDiagnosis }])}>
                  <Plus className="h-3.5 w-3.5" />Add Diagnosis
                </Button>
              </div>

              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Procedure (SNOMED CT)</h4>
                {procedures.map((p, i) => (
                  <div key={i} className="flex gap-2 items-start">
                    <Input
                      value={p.code}
                      onChange={(e) => setProcedures(procedures.map((x, j) => (j === i ? { ...x, code: e.target.value } : x)))}
                      placeholder="SNOMED code, e.g. 77343006"
                      className="w-40 font-mono"
                    />
                    <Input
                      value={p.display}
                      onChange={(e) => setProcedures(procedures.map((x, j) => (j === i ? { ...x, display: e.target.value } : x)))}
                      placeholder="Description, e.g. Angiography"
                      className="flex-1"
                    />
                    <Button type="button" variant="outline" size="icon" onClick={() => setProcedures(procedures.filter((_, j) => j !== i))} disabled={procedures.length === 1}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                ))}
                <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => setProcedures([...procedures, { ...emptyProcedure }])}>
                  <Plus className="h-3.5 w-3.5" />Add Procedure
                </Button>
              </div>

              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Claim Line Items</h4>
                {lineItems.map((it, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-start">
                    <Input
                      value={it.code}
                      onChange={(e) => setLineItems(lineItems.map((x, j) => (j === i ? { ...x, code: e.target.value } : x)))}
                      placeholder="SNOMED code"
                      className="col-span-2 font-mono"
                    />
                    <Input
                      value={it.display}
                      onChange={(e) => setLineItems(lineItems.map((x, j) => (j === i ? { ...x, display: e.target.value } : x)))}
                      placeholder="Service / item description"
                      className="col-span-5"
                    />
                    <Input
                      type="number"
                      value={it.unitPrice || ''}
                      onChange={(e) => setLineItems(lineItems.map((x, j) => (j === i ? { ...x, unitPrice: Number(e.target.value) } : x)))}
                      placeholder="Unit price"
                      className="col-span-2"
                    />
                    <Input
                      type="number"
                      value={it.net || ''}
                      onChange={(e) => setLineItems(lineItems.map((x, j) => (j === i ? { ...x, net: Number(e.target.value) } : x)))}
                      placeholder="Net amount"
                      className="col-span-2"
                    />
                    <Button type="button" variant="outline" size="icon" className="col-span-1" onClick={() => setLineItems(lineItems.filter((_, j) => j !== i))} disabled={lineItems.length === 1}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                ))}
                <div className="flex items-center justify-between">
                  <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => setLineItems([...lineItems, { ...emptyLineItem }])}>
                    <Plus className="h-3.5 w-3.5" />Add Line Item
                  </Button>
                  <p className="text-sm font-medium">Total: ₹{total.toLocaleString('en-IN')}</p>
                </div>
              </div>

              <MultiDocGallery documents={documents} onAdd={handleDocumentsChange} onRemove={removeDocument} />
            </div>
          )}

          {/* Step navigation */}
          <div className="flex items-center justify-between pt-4 border-t">
            <Button type="button" variant="outline" className="gap-1.5" onClick={handleBack} disabled={currentStep === 0}>
              <ChevronLeft className="h-4 w-4" /> Back
            </Button>
            {currentStep < STEPS.length - 1 ? (
              <Button type="button" className="gap-1.5" onClick={handleNext}>
                Next Step <ChevronRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button className="gap-2" onClick={handleSavePatient} disabled={!!duplicateMatch}>
                <UserPlus className="h-4 w-4" /> {editingId ? 'Update Patient' : 'Save Patient'}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      ) : (
      <Card>
        <CardHeader>
          <CardTitle>Registered Patients</CardTitle>
          <CardDescription>Everyone registered so far — expand a row for full details</CardDescription>
        </CardHeader>
        <CardContent>
          {patients.length === 0 ? (
            <p className="text-sm text-gray-500">No patients registered yet</p>
          ) : (
            <Accordion type="single" collapsible className="w-full">
              {patients.map((p) => (
                <AccordionItem key={p.id} value={p.id}>
                  <AccordionTrigger>
                    <div className="flex items-center gap-3">
                      {p.patientPhoto?.previewUrl ? (
                        <img src={p.patientPhoto.previewUrl} alt={p.fullName} className="h-8 w-8 rounded-full object-cover border" />
                      ) : (
                        <Users className="h-4 w-4 text-gray-400" />
                      )}
                      <span className="font-medium">{p.fullName}</span>
                      <span className="text-xs text-gray-500">
                        {p.abhaNumber ? `ABHA: ${p.abhaNumber}` : p.aadhaarNumber ? `Aadhaar: ${p.aadhaarNumber}` : ''}
                      </span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="space-y-4">
                    <div className="flex justify-end">
                      <Button type="button" variant="outline" size="sm" onClick={() => loadPatientForEdit(p)}>
                        Edit / Add Info
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                      <div><p className="text-xs text-gray-500">Gender</p><p className="font-medium capitalize">{p.gender || '—'}</p></div>
                      <div><p className="text-xs text-gray-500">Date of Birth</p><p className="font-medium">{p.dob || '—'}</p></div>
                      <div><p className="text-xs text-gray-500">Mobile Number</p><p className="font-medium">{p.mobile || '—'}</p></div>
                      <div><p className="text-xs text-gray-500">Aadhaar Number</p><p className="font-medium">{p.aadhaarNumber || '—'}</p></div>
                      <div><p className="text-xs text-gray-500">ABHA Number</p><p className="font-medium">{p.abhaNumber || '—'}</p></div>
                      <div><p className="text-xs text-gray-500">Treating Doctor</p><p className="font-medium">{p.doctorName || '—'} {p.doctorLicense && `(${p.doctorLicense})`}</p></div>
                      <div><p className="text-xs text-gray-500">Hospital</p><p className="font-medium">{p.hospitalName || '—'}</p></div>
                      <div><p className="text-xs text-gray-500">Insurer</p><p className="font-medium">{p.insurerName || '—'}</p></div>
                      <div><p className="text-xs text-gray-500">Policy Number</p><p className="font-medium">{p.policyNumber || '—'}</p></div>
                    </div>

                    {(p.patientPhoto?.previewUrl || p.prescription) && (
                      <div className="flex flex-wrap gap-4">
                        {p.patientPhoto?.previewUrl && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Photograph</p>
                            <img src={p.patientPhoto.previewUrl} alt="Patient" className="h-20 w-20 rounded object-cover border" />
                          </div>
                        )}
                        {p.prescription && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Prescription</p>
                            {p.prescription.previewUrl ? (
                              <img src={p.prescription.previewUrl} alt="Prescription" className="h-20 rounded border" />
                            ) : (
                              <div className="flex items-center gap-1.5 rounded border bg-red-50 dark:bg-red-950/30 px-2.5 py-1.5 text-sm">
                                <FileText className="h-3.5 w-3.5 text-red-500" /> {p.prescription.name}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {(p.generalFindings || p.familyHistoryDiabetes || p.familyHistoryHypertension || p.familyHistoryHeartDisease || p.familyHistoryStroke) && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">General Findings & Family History</p>
                        <p className="text-sm">
                          {p.generalFindings && `Findings: ${p.generalFindings}. `}
                          Diabetes: {p.familyHistoryDiabetes || 'None'}, Hypertension: {p.familyHistoryHypertension || 'None'}, Heart Disease: {p.familyHistoryHeartDisease || 'None'}, Stroke: {p.familyHistoryStroke || 'None'}
                        </p>
                      </div>
                    )}
                    {(p.personalHistoryDiet || p.personalHistoryKnownAllergies || p.personalHistoryHabitsAddictions || p.personalHistoryNutrition || p.personalHistoryAppetite || p.personalHistoryBowels) && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Personal History</p>
                        <p className="text-sm">
                          Diet: {p.personalHistoryDiet || 'Normal'}, Known Allergies: {p.personalHistoryKnownAllergies || 'None'}, Habits/Addictions: {p.personalHistoryHabitsAddictions || 'None'}, Nutrition: {p.personalHistoryNutrition || 'Normal'}, Appetite: {p.personalHistoryAppetite || 'Normal'}, Bowels: {p.personalHistoryBowels || 'Normal'}
                        </p>
                      </div>
                    )}
                    {p.diagnoses.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Diagnosis (ICD-10)</p>
                        <p className="text-sm">{p.diagnoses.map((d) => `${d.code} — ${d.display}`).join(', ')}</p>
                      </div>
                    )}
                    {p.procedures.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Procedure (SNOMED CT)</p>
                        <p className="text-sm">{p.procedures.map((pr) => `${pr.code} — ${pr.display}`).join(', ')}</p>
                      </div>
                    )}
                    {p.lineItems.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-500 mb-1">Line Items</p>
                        <p className="text-sm">
                          Total: ₹{p.lineItems.reduce((sum, it) => sum + (it.net || 0), 0).toLocaleString('en-IN')}
                        </p>
                      </div>
                    )}
                    {p.documents.length > 0 && (
                      <div>
                        <p className="text-xs text-gray-500 mb-2">Additional Documents ({p.documents.length})</p>
                        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
                          {p.documents.map((doc, i) => (
                            <div key={i} className="rounded-lg border bg-gray-50 dark:bg-gray-900/40 p-1.5">
                              {doc.previewUrl ? (
                                <img src={doc.previewUrl} alt={doc.name} className="h-16 w-full rounded object-cover border" />
                              ) : (
                                <div className="flex h-16 w-full items-center justify-center rounded border bg-red-50 dark:bg-red-950/30">
                                  <FileText className="h-5 w-5 text-red-500" />
                                </div>
                              )}
                              <p className="mt-1 truncate text-[11px] text-gray-600 dark:text-gray-300">{doc.name}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </CardContent>
      </Card>
      )}
    </div>
  );
}
