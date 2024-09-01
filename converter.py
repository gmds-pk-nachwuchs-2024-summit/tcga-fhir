import argparse
import uuid
from pathlib import Path

from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.procedure import Procedure
from fhir.resources.researchsubject import ResearchSubject
from fhir.resources.researchstudy import ResearchStudy, ResearchStudyProgressStatus
from fhir.resources.codeableconcept import CodeableConcept

from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.age import Age

DATA_PATH = "data/paad_tcga_pan_can_atlas_2018_clinical_data.tsv"
PATIENT_ID_SYSTEM = "https://www.gmds.de/pk-nachwuchs/patient"
STUDY_PATIENT_ID_SYSTEM = "https://www.cbioportal.org/patient"
STUDY_ID_SYSTEM = "https://www.cbioportal.org/study"
STUDY_ID_VALUE = "paad_tcga_pan_can_atlas_2018"

patients_uuid = dict()
research_subject_uuid = dict()
condition_uuid = dict()
procedure_uuid = dict()


def create_research_study():
    identifier = Identifier.construct()
    identifier.system = STUDY_ID_SYSTEM
    identifier.value = "paad_tcga_pan_can_atlas_2018"

    research_study = ResearchStudy.construct(status="active")
    research_study.identifier = [identifier]
    research_study.name = "tcga_pancreatic_adenocarcinoma"
    research_study.title = "Pancreatic Adenocarcinoma (TCGA, PanCancer Atlas)"
    research_study.version = "1.0.0"
    research_study.id = research_study_id
    research_study.progressStatus = [ResearchStudyProgressStatus(
        **{
            "state": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/research-study-status",
                        "code": "completed",
                        "display": "Completed",
                    }
                ]
            }
        }
    )]

    return research_study


def create_patient(study_subject_id, patient_id, gender, living_status):
    pat_identifier = Identifier.construct()
    pat_identifier.system = PATIENT_ID_SYSTEM
    pat_identifier.value = patient_id.lower()

    patients_uuid[study_subject_id] = str(uuid.uuid4())

    pat = Patient.construct()
    pat.identifier = [pat_identifier]
    pat.gender = gender.lower()
    pat.deceasedBoolean = living_status
    pat.id = patients_uuid[study_subject_id]
    return pat


def create_research_subject(study_patient_id):
    pat_ref = Reference.construct(reference=f"Patient/{patients_uuid[study_patient_id]}")
    study_ref = Reference.construct(reference=f"ResearchStudy/{research_study_id}")

    research_subject_uuid[study_patient_id] = str(uuid.uuid4())

    research_sub = ResearchSubject.construct(status="active")
    research_sub.subject = pat_ref
    research_sub.study = study_ref

    pat_identifier = Identifier.construct()
    pat_identifier.system = STUDY_PATIENT_ID_SYSTEM
    pat_identifier.value = study_patient_id
    research_sub.identifier = [pat_identifier]
    research_sub.id = research_subject_uuid[study_patient_id]
    return research_sub


def get_label(icd_10_code):
    match icd_10_code:
        case "C25.0":
            return "Bösartige Neubildung: Pankreaskopf"
        case "C25.1":
            return "Bösartige Neubildung: Pankreaskörper"
        case "C25.2":
            return "Bösartige Neubildung: Pankreasschwanz"
        case "C25.3":
            return "Bösartige Neubildung: Ductus pancreaticus"
        case "C25.4":
            return "Bösartige Neubildung: Endokriner Drüsenanteil des Pankreas"
        case "C25.7":
            return "Bösartige Neubildung: Sonstige Teile des Pankreas"
        case "C25.8":
            return "Bösartige Neubildung: Pankreas, mehrere Teilbereiche überlappend"
        case "C25.9":
            return "Bösartige Neubildung: Pankreas, nicht näher bezeichnet"


def create_condition(study_subject_id, icd_code, onset_age):
    age = Age.construct()
    age.value = float(onset_age)
    age.unit = "a"  # UCUM unit for year

    condition = Condition.construct(clinicalStatus={
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
            "display": "Active",
            "code": "active"
        }]
    })
    condition.subject = Reference.construct(
        reference=f"Patient/{patients_uuid[study_subject_id]}"
    )
    condition.onsetAge = age


    condition_uuid[study_subject_id] = str(uuid.uuid4())
    condition.id = condition_uuid[study_subject_id]

    condition_codeable = CodeableConcept.construct()
    condition_codeable.coding = list()
    condition_codeable.coding.append(
        {
            "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
            "code": icd_code,
            "display": get_label(icd_code),
        }
    )
    condition.code = condition_codeable

    return condition


def create_procedure(study_subject_id):
    procedure = Procedure.construct(status="completed")
    procedure.subject = Reference.construct(
        reference=f"Patient/{patients_uuid[study_subject_id]}"
    )

    procedure_uuid[study_subject_id] = str(uuid.uuid4())
    procedure.id = procedure_uuid[study_subject_id]

    radiation_codeable = CodeableConcept.construct()
    radiation_codeable.coding = list()
    radiation_codeable.coding.append(
        {
            "system": "http://snomed.info/sct",
            "code": "1287742003",
            "display": "Radiotherapy (procedure)",
        }
    )
    procedure.code = radiation_codeable

    return procedure


def create_bundle(data_values):
    transaction_bundle = Bundle.construct()
    transaction_bundle.type = "transaction"

    study_subject_id = data_values[1]
    onset_age = data_values[3]
    icd_10_code = data_values[24]
    is_alive = True if data_values[35] == "0:LIVING" else False
    secondary_pat_id = data_values[36]
    radio_therapy = True if data_values[46] == "Yes" else False
    gender = data_values[50]

    pat_entry_request = BundleEntryRequest.construct(url="Patient", method="POST")
    pat_entry_request.ifNoneExist = (
        f"identifier={PATIENT_ID_SYSTEM}|{secondary_pat_id.lower()}"
    )

    research_study_request = BundleEntryRequest.construct(
        url="ResearchStudy", method="POST"
    )
    research_study_request.ifNoneExist = (
        f"identifier={STUDY_ID_SYSTEM}|{STUDY_ID_VALUE}"
    )

    research_subject_request = BundleEntryRequest.construct(
        url="ResearchSubject", method="POST"
    )
    research_subject_request.ifNoneExist = (
        f"identifier={STUDY_PATIENT_ID_SYSTEM}|{study_subject_id}"
    )

    pat = create_patient(
        study_subject_id=study_subject_id,
        patient_id=secondary_pat_id,
        gender=gender,
        living_status=is_alive,
    )
    research_subject = create_research_subject(study_patient_id=study_subject_id)
    condition = create_condition(study_subject_id, icd_10_code, onset_age)

    procedure_entry = None

    if radio_therapy:
        procedure_entry = BundleEntry.construct()
        procedure_entry.resource = create_procedure(study_subject_id=study_subject_id)
        procedure_entry.request = BundleEntryRequest.construct(
            url="Procedure", method="POST"
        )
        procedure_entry.fullUrl = f"Procedure/{procedure_uuid[study_subject_id]}"

    pat_entry = BundleEntry.construct()
    pat_entry.resource = pat
    pat_entry.request = pat_entry_request
    pat_entry.fullUrl = f"Patient/{patients_uuid[study_subject_id]}"

    research_subject_entry = BundleEntry.construct()
    research_subject_entry.resource = research_subject
    research_subject_entry.request = research_subject_request
    research_subject_entry.fullUrl = f"ResearchSubject/{research_subject_uuid[study_subject_id]}"

    condition_entry = BundleEntry.construct()
    condition_entry.resource = condition
    condition_entry.request = BundleEntryRequest.construct(
        url="Condition", method="POST"
    )
    condition_entry.fullUrl = f"Condition/{condition_uuid[study_subject_id]}"
    transaction_bundle.entry = [
        pat_entry,
        research_subject_entry,
        condition_entry,
    ]

    if procedure_entry:
        transaction_bundle.entry.append(procedure_entry)

    return transaction_bundle, study_subject_id


if __name__ == "__main__":

    with open(DATA_PATH) as data_file:
        lines = data_file.readlines()

    parser = argparse.ArgumentParser()
    parser.add_argument("--research-study-id")
    args = parser.parse_args()
    out_path = Path("bundles")
    out_path.mkdir(exist_ok=True)
    if not args.research_study_id:
        research_study_id = str(uuid.uuid4())
        study_out_name = out_path.joinpath(f"study.json")
        with open(study_out_name, "w") as of:
            print(study_out_name)
            of.write(create_research_study().json(ensure_ascii=False, indent=2))
        exit(0)
    else:
        research_study_id = args.research_study_id

    for line in lines[1:]:
        values = line.split("\t")
        bundle, subject_id = create_bundle(values)

        out_name = out_path.joinpath(f"{subject_id}.json")
        with open(out_name, "w") as of:
            print(out_name)
            of.write(bundle.json(ensure_ascii=False, indent=2))
