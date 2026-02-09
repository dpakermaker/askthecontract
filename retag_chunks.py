import pickle
import os

CHUNKS_PATH = os.path.join("contracts", "NAC", "chunks.pkl")

with open(CHUNKS_PATH, "rb") as f:
    chunks = pickle.load(f)
print(f"Loaded {len(chunks)} chunks")

LOA_MAP = [
    (266, 268, "LOA #1 - HIMS Program"),
    (269, 271, "LOA #2 - Drug & Alcohol Testing"),
    (272, 280, "LOA #3 - Seniority Integration"),
    (281, 287, "LOA #4 - Training & Qualification"),
    (288, 289, "LOA #5 - Section 14 Implementation Schedule"),
    (290, 292, "LOA #6 - Reserve Duty"),
    (293, 297, "LOA #7 - Scheduling"),
    (298, 300, "LOA #8 - Benefits"),
    (301, 303, "LOA #9 - Domicile"),
    (304, 306, "LOA #10 - Vacancy & Displacement"),
    (307, 311, "LOA #11 - Compensation"),
    (312, 314, "LOA #12 - Training Program"),
    (315, 319, "LOA #13 - B767 Retroactive Pay"),
    (320, 335, "LOA #15 - Check Airman & Instructor Pay (Original)"),
    (336, 351, "LOA #15 - Check Airman & Instructor Pay (Amended)"),
    (352, 352, "LOA #16 - Cover Letter"),
    (353, 377, "LOA #16 - Acquisition Protections"),
]
MOU_MAP = [
    (378, 378, "Memorandums of Understanding - Title Page"),
    (379, 380, "MOU #1 - PTO Day Conversion and Redistribution"),
    (381, 381, "MOU #2 - Positive Contact Responsibilities"),
    (382, 382, "MOU #3 - R2 Reserve Reassignment"),
    (383, 385, "MOU #4 - Reserve Assignment Reassignment"),
    (386, 387, "MOU #5 - Pay Implications During Monthly Bid"),
    (388, 389, "MOU #6 - Company Paid Move Entitlements"),
    (390, 390, "MOU #7 - Check Airman Pay"),
    (391, 391, "MOU #8 - Pay When Changing Positions"),
    (392, 394, "MOU #9 - Check Airman Line Integration & SAP"),
]
APPENDIX_MAP = [
    (66, 66, "Appendix A - Pay Rates"),
    (252, 253, "Appendix 29-A - Dues Checkoff"),
]

page_label = {}
for start, end, label in LOA_MAP + MOU_MAP + APPENDIX_MAP:
    for p in range(start, end + 1):
        page_label[p] = label

changed = 0
for chunk in chunks:
    page = chunk.get("page", 0)
    if page in page_label:
        if chunk.get("section") != page_label[page]:
            chunk["section"] = page_label[page]
            changed += 1

with open(CHUNKS_PATH, "wb") as f:
    pickle.dump(chunks, f)

print(f"Re-tagged {changed} chunks")
print("Done!")
