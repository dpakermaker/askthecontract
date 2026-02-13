"""
Northern Air Cargo (NAC) JCBA — Contract Configuration
========================================================
This file contains ALL data specific to the NAC pilot contract.

TO ADD A NEW AIRLINE:
1. Copy this file to contracts/[airline_code]/contract_data.py
2. Change ALL the values to match the new airline's contract
3. Add the new contract_id to MODULE_MAP in streamlit_app.py
4. Add chunks.pkl and embeddings.pkl to the same folder
5. Deploy

Everything in this file is NAC-specific. The main app (streamlit_app.py)
contains only the universal logic that works for any airline.
"""

from datetime import datetime

# ============================================================
# CONTRACT IDENTITY
# ============================================================
AIRLINE_NAME = "Northern Air Cargo"
CONTRACT_NAME = "JCBA"
CONTRACT_ID = "nac_jcba"

# ============================================================
# PAY RATES
# ============================================================

# Date of Signing — used to compute annual pay increases
DOS_DATE = datetime(2018, 7, 24)
PAY_INCREASE_PERCENT = 0.02  # 2% per year per Section 3.B.3

# DOS rates from Appendix A (July 24, 2018)
PAY_RATES_DOS = {
    'B737': {
        'Captain': {1: 133.08, 2: 137.40, 3: 141.87, 4: 146.48, 5: 151.24, 6: 156.16, 7: 161.23, 8: 166.47, 9: 171.88, 10: 177.47, 11: 183.23, 12: 189.19},
        'First Officer': {1: 83.73, 2: 88.25, 3: 92.97, 4: 97.91, 5: 103.07, 6: 108.46, 7: 114.09, 8: 119.98, 9: 123.87, 10: 127.90, 11: 132.06, 12: 136.34},
    }
}

# 2% annual increase computed dynamically — never goes stale
def _compute_pay_increases():
    """Count completed DOS anniversaries."""
    now = datetime.now()
    anniversaries = now.year - DOS_DATE.year
    if (now.month, now.day) < (DOS_DATE.month, DOS_DATE.day):
        anniversaries -= 1
    return max(0, anniversaries)

PAY_INCREASES = _compute_pay_increases()
PAY_MULTIPLIER = (1 + PAY_INCREASE_PERCENT) ** PAY_INCREASES

# ============================================================
# PER DIEM
# ============================================================
PER_DIEM_BASE_DOMESTIC = 56     # Section 6.C.2.a
PER_DIEM_BASE_INTERNATIONAL = 72  # Section 6.C.2.b
PER_DIEM_ANNUAL_INCREASE = 1    # Section 6.C.2.c — $1/day per anniversary
PER_DIEM_KEYWORDS = ['per diem', 'per diem rate', 'what is per diem', 'how much is per diem',
                     'per diem amount', 'meal allowance', 'daily meal', 'per diem pay']

# ============================================================
# CONTEXT PACKS — Essential pages per topic
# When a pilot asks about "pay", pull these pages.
# ============================================================
CONTEXT_PACKS = {
    # PAY questions — Section 3 core + Appendix A + Reserve Pay + Check Airman premiums
    'pay': {
        'pages': [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 200, 322, 338,
                  386, 387,  # MOU #5: MPG/line PCH implications
                  390,       # MOU #7: Check Airman Pay
                  391,       # MOU #8: Pay When Changing Positions
        ],
        'embedding_top_n': 15,
        'max_total': 30,
    },
    # RESERVE questions — Section 15 + MOU reserve + reserve pay
    'reserve': {
        'pages': [193, 194, 195, 196, 197, 198, 199, 200,
                  381,       # MOU #2: Positive Contact
                  382,       # MOU #3: Reassignment to Trip Pairings
                  383, 384, 385,  # MOU #4: Reserve Reassignment types
        ],
        'embedding_top_n': 15,
        'max_total': 30,
    },
    # SCHEDULING / DAYS OFF — Section 14 key provisions + LOA #15 scheduling + extensions
    'scheduling': {
        'pages': [160, 161, 168, 169, 170, 171, 172, 173, 177, 180, 181, 185, 188, 190,
                  326, 328, 342, 344,  # LOA #15 scheduling
                  383, 384, 385,       # MOU #4: Reserve Reassignment
                  386, 387,            # MOU #5: Line construction/MPG
        ],
        'embedding_top_n': 15,
        'max_total': 30,
    },
    # BENEFITS — Section 5 (retirement, insurance)
    'benefits': {
        'pages': [71, 72, 73, 74, 75, 76, 77, 78],
        'embedding_top_n': 10,
        'max_total': 25,
    },
    # TRAINING — Section 12 + Section 22 + Check Airman LOA/MOU
    'training': {
        'pages': [145, 146, 147, 148, 149, 150, 151, 152, 231, 232, 233, 234,
                  323,       # LOA #15: Check Airman Ghost Bid/scheduling
                  390,       # MOU #7: Check Airman Pay
                  392,       # MOU #9: Check Airman Line Integration
        ],
        'embedding_top_n': 15,
        'max_total': 30,
    },
    # HOURS OF SERVICE — Section 13 + Positive Contact MOU
    'hours': {
        'pages': [151, 152, 153, 154, 155, 156, 157, 158,
                  381,  # MOU #2: Positive Contact (ties to Section 13.H)
        ],
        'embedding_top_n': 10,
        'max_total': 25,
    },
    # VACATION / LEAVE / SICK — Sections 8, 9, 10 + PTO + MOU #1
    'vacation': {
        'pages': [105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 121, 122, 123, 124, 125, 126, 127, 129, 130,
                  131, 132, 133, 134, 135, 136, 137,  # Section 10: Sick Leave
                  139,
                  379,  # MOU #1: PTO Day Conversion
        ],
        'embedding_top_n': 10,
        'max_total': 30,
    },
    # SENIORITY / FURLOUGH — Sections 4 & 17 + LOA #11 vacancy fences
    'seniority': {
        'pages': [204, 205, 206, 207, 208, 209, 210, 211, 212, 213,
                  307, 308, 309, 310, 311,  # LOA #11: Vacancy filling/seniority fences
        ],
        'embedding_top_n': 10,
        'max_total': 25,
    },
    # GRIEVANCE / ARBITRATION — Sections 19 & 20
    'grievance': {
        'pages': [216, 217, 218, 219, 220, 221, 222, 223, 224, 225],
        'embedding_top_n': 10,
        'max_total': 25,
    },
    # EXPENSES / LODGING — Section 6 + MOU #6 Paid Move
    'expenses': {
        'pages': [86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104,
                  388,  # MOU #6: Company Paid Move Entitlement
        ],
        'embedding_top_n': 10,
        'max_total': 25,
    },
}

# Map question categories to context pack keys
CATEGORY_TO_PACK = {
    'Pay → Hourly Rate': 'pay',
    'Pay → Daily Pay Guarantee': 'pay',
    'Pay → Duty Rig': 'pay',
    'Pay → Trip Rig / TAFD': 'pay',
    'Pay → Overtime / Premium': 'pay',
    'Pay → Junior Assignment Premium': 'pay',
    'Pay → General Calculation': 'pay',
    'Reserve → Types & Definitions': 'reserve',
    'Reserve → FIFO': 'reserve',
    'Reserve → Availability / RAP': 'reserve',
    'Reserve → Day-Off Reassignment': 'reserve',
    'Scheduling → Days Off': 'scheduling',
    'Scheduling → Rest Periods': 'hours',
    'Scheduling → Line Construction': 'scheduling',
    'Scheduling → Reassignment': 'scheduling',
    'Scheduling → Duty Limits': 'hours',
    'Training': 'training',
    'Seniority': 'seniority',
    'Grievance': 'grievance',
    'TDY': 'scheduling',
    'Vacation / Leave': 'vacation',
    'Benefits': 'benefits',
    'Furlough': 'seniority',
    'Expenses / Per Diem': 'expenses',
    'Sick Leave': 'vacation',
    'Deadhead': 'pay',
    'Hours of Service': 'hours',
}


# ============================================================
# PROVISION CHAINS — Keyword → supplemental pages
# Cross-references that fire regardless of topic category.
# ============================================================
PROVISION_CHAINS = {
    # Check Airman / Instructor topics → all Check Airman LOA/MOU pages
    'check airman': [59, 60, 322, 323, 338, 339, 390, 392],
    'instructor pilot': [59, 60, 322, 323, 338, 339, 390, 392],
    'apd': [59, 60, 322, 323, 338, 339, 390, 392],
    'ghost bid': [322, 323, 338, 339],
    '175%': [59, 60],
    '175 percent': [59, 60],
    'check airman pay': [59, 60, 390],
    'administrative assignment': [59, 60],
    'admin assignment': [59, 60],
    # Positive Contact → MOU #2 + Section 13.H
    'positive contact': [154, 155, 381],
    'schedule change': [154, 155, 381],
    'contact method': [381],
    # Reserve reassignment → MOU #3, #4
    'reassign': [382, 383, 384, 385],
    'r-1 to r-2': [383, 384, 385],
    'r-2 to r-1': [383, 384, 385],
    'reserve type': [383, 384, 385],
    # PTO conversion → MOU #1
    'pto conversion': [379],
    'pto bank': [379],
    'pto day': [379],
    # Paid move → MOU #6
    'paid move': [388],
    'company move': [388],
    'relocation': [388],
    # Position change pay → MOU #8
    'position change': [391],
    'upgrade pay': [391],
    'changing position': [391],
    # Vacancy / seniority fences → LOA #11
    'vacancy': [307, 308, 309, 310, 311],
    'displacement': [307, 308, 309, 310, 311],
    'fence period': [307, 308, 309, 310, 311],
    # MPG / line value → MOU #5
    'mpg': [386, 387],
    'line value': [386, 387],
    'holdback': [386, 387],
    'hold-back': [386, 387],
    # Scope / acquisition → LOA #7, #9, #10, #16
    'scope': [293, 294, 295, 301, 302, 304, 305, 353, 354],
    'carrier a': [353, 354, 355, 356, 357, 358],
    'affiliate': [293, 294, 295],
    'subcontract': [304, 305, 306, 353, 357],
    # ASAP / FOQA → LOA #3, #4
    'asap': [281, 282, 283, 284, 285],
    'foqa': [272, 273, 274, 275, 276, 277],
    # Extension → Section 14.N
    'extension': [185, 186],
    # Landing credit → Section 3.T
    'landing credit': [63],
    'landing premium': [63],
    # Hostile area → Section 3.U
    'hostile area': [63],
    'hostile operation': [63],
    # NRFO → Section 3.L
    'nrfo': [58],
    'non-routine': [58],
    # Deadhead pay/rules → Section 3.I, 3.K
    'deadhead': [56, 57],
    'deadhead pay': [56, 57],
    'deadhead rest': [56, 57, 154, 155],
    'positioning': [56, 57],
    # Open time / VPA → Section 14.M, 14.N
    'open time': [183, 184, 185, 186],
    'vpa': [183, 184, 185, 186],
    'voluntary pickup': [183, 184, 185, 186],
    'pick up': [183, 184, 185, 186],
    'trip trade': [183, 184],
    # Per diem → Section 6.C (primary) + Section 3 references
    'per diem': [57, 58, 99, 100, 101],
    'meal allowance': [99, 100, 101],
    'meal money': [99, 100, 101],
    'hotel': [99, 100, 101, 102, 103],
    'lodging': [99, 100, 101, 102, 103],
    # Sick leave → Section 10
    'sick': [131, 132, 133, 134, 135, 136, 137],
    'sick call': [131, 132, 133, 134, 135],
    'sick pay': [131, 132, 133, 134],
    'calling in sick': [131, 132, 133],
    'illness': [131, 132, 133, 134],
    # Furlough / recall → Section 18
    'furlough': [204, 205, 206, 207, 208, 209, 210],
    'recall': [204, 205, 206, 207, 208, 209, 210],
    'layoff': [204, 205, 206, 207],
    'reduction in force': [204, 205, 206],
    # Probation / new hire → Section 18
    'probation': [204, 205, 211, 212],
    'probationary': [204, 205, 211, 212],
    'new hire': [204, 205, 211, 212],
    # Training → Section 12
    'training pay': [145, 146, 147, 148, 322, 323, 390],
    'recurrent': [145, 146, 147, 148],
    'check ride': [145, 146, 147, 148, 322, 323],
    'simulator': [145, 146, 147, 148],
    'ground school': [145, 146, 147],
    'initial operating': [145, 146, 147, 148],
    'ioe': [145, 146, 147, 148],
    # Insurance / benefits → Section 9
    'health insurance': [86, 87, 88, 89, 90],
    '401k': [95, 96, 97, 98],
    '401(k)': [95, 96, 97, 98],
    'life insurance': [91, 92, 93],
    'disability': [93, 94],
    'dental': [86, 87, 88],
    'vision': [86, 87, 88],
    # Upgrade / downgrade
    'upgrade': [204, 205, 206, 391],
    'downgrade': [204, 205, 206, 391],
    'bid for captain': [204, 205, 206],
    # Commuting
    'commut': [56, 57, 154, 155],
    'commuter policy': [56, 57],
    # Direct Section references by number
    'section 3': [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63],
    'section 8': [105, 106, 107, 108, 109, 110, 111, 112, 113],
    'section 9': [86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98],
    'section 10': [131, 132, 133, 134, 135, 136, 137],
    'section 12': [145, 146, 147, 148, 149, 150],
    'section 13': [151, 152, 153, 154, 155, 156, 157, 158],
    'section 14': [160, 161, 168, 169, 170, 171, 172, 173, 177, 180, 181, 185, 188, 190],
    'section 15': [193, 194, 195, 196, 197, 198, 199, 200],
    'section 18': [204, 205, 206, 207, 208, 209, 210, 211, 212, 213],
    'section 19': [216, 217, 218, 219, 220, 221, 222, 223, 224, 225],
    # Direct MOU references by number
    'mou #1': [379],
    'mou #2': [381],
    'mou #3': [382],
    'mou #4': [383, 384, 385],
    'mou #5': [386, 387],
    'mou #6': [388],
    'mou #7': [390],
    'mou #8': [391],
    'mou #9': [392],
    'mou 1': [379],
    'mou 2': [381],
    'mou 3': [382],
    'mou 4': [383, 384, 385],
    'mou 5': [386, 387],
    'mou 6': [388],
    'mou 7': [390],
    'mou 8': [391],
    'mou 9': [392],
    # Direct LOA references by number
    'loa #3': [281, 282, 283, 284, 285],
    'loa #4': [272, 273, 274, 275, 276, 277],
    'loa #7': [293, 294, 295],
    'loa #9': [301, 302],
    'loa #10': [304, 305, 306],
    'loa #11': [307, 308, 309, 310, 311],
    'loa #15': [326, 328, 338, 339, 342, 344],
    'loa #16': [353, 354, 355, 356, 357, 358],
    'loa 3': [281, 282, 283, 284, 285],
    'loa 4': [272, 273, 274, 275, 276, 277],
    'loa 7': [293, 294, 295],
    'loa 9': [301, 302],
    'loa 10': [304, 305, 306],
    'loa 11': [307, 308, 309, 310, 311],
    'loa 15': [326, 328, 338, 339, 342, 344],
    'loa 16': [353, 354, 355, 356, 357, 358],
}

# ============================================================
# FORCE-INCLUDE RULES — Guaranteed chunk retrieval
# When keywords match, these phrases MUST be found in chunks.
# ============================================================
FORCE_INCLUDE_RULES = {
    'days_off': {
        'trigger_keywords': ['day off', 'days off', 'rest period', 'week off', 'time off', 'duty free', 'one day per week', 'day per week', 'weekly day', 'days a week', 'off per week', 'off a week'],
        'must_include_phrases': [
            'regular line shall be scheduled with at least one (1) day off in any seven',
            'composite line shall be scheduled with at least one (1) day off in any seven',
            'shall receive at least one (1) twenty-four (24) hour rest period free from all duty within any seven',
            'schedule the pilot for one (1) day off in every seven (7) days',
            'minimum scheduled days off in all constructed initial lines shall be thirteen',
            'shall have at least two (2) separate periods of at least three (3) consecutive days off',
            'scheduled to have a minimum of one (1) day off during every seven (7) consecutive days of training',
            'minimum rest requirements for a pilot who is awarded a domicile flex line',
            # Cross-reference: 0200 LDT rule for assignments into day off
            'assignment may be scheduled up to 0200 local domicile time',
            # Cross-reference: Day Off overtime pay conditions
            'overtime premium',
        ]
    },
    'pay': {
        'trigger_keywords': ['pay', 'rate', 'hourly', 'salary', 'wage', 'compensation', 'dpg', 'daily pay guarantee', 'duty rig', 'trip rig', 'pch', 'make per hour', 'overtime', '150%', '200%', '175%', 'premium'],
        'must_include_phrases': [
            'daily pay guarantee',
            'one (1) pch for every two (2) hours',
            'trip rig',
            'open time premium',
            'junior assignment premium',
            'monthly pay guarantee',
            'overtime premium',
        ]
    },
    'reserve_day_off': {
        'trigger_keywords': ['reserve', 'r-1', 'r-2', 'r-3', 'r-4', 'r1', 'r2', 'r3', 'r4', 'rap', 'fifo'],
        'must_include_phrases': [
            # 0200 LDT rule - assignments can go up to 0200 into day off
            'assignment may be scheduled up to 0200 local domicile time',
            # Reserve cannot be assigned conflicting with day off
            'shall not be assigned a trip pairing or other company-directed',
            # Auto-release from RAP
            'has not assigned a pilot performing a rap to a trip pairing or other company-directed assignment within two (2) hours',
            # Extension into day off for reserve
            'if a reserve pilot departs his domicile and incurs a delay',
            # 12-hour RAP max
            'r-1 and r-2 rap shall not be scheduled to exceed twelve (12) hours',
            # Duty time limits apply to reserve
            'the duty time limitations and rest requirements for a pilot on a rap',
            # Section 14.N extension provisions (needed when reserve duty extends past RAP)
            'extension procedures',
            'extension shall not cause',
            'a pilot shall not be extended more than one (1) time per month',
        ]
    },
    'reserve_pay': {
        'trigger_keywords': ['reserve pay', 'reserve compensation', 'rap pay', 'r-1 pay', 'r-2 pay', 'r1 pay', 'r2 pay'],
        'must_include_phrases': [
            'daily pay guarantee',
            'one (1) pch for every two (2) hours',
            'trip rig',
            'overtime premium',
            'a pilot who is scheduled for reserve or performs an assignment while on reserve shall be paid',
        ]
    },
    'midnight_day_off': {
        'trigger_keywords': ['midnight', 'past midnight', 'into day off', 'into his day', 'into a day off', 'work into', 'fly into', 'fly past', '0200', 'next day off', 'friday'],
        'must_include_phrases': [
            # THE key rule: 0200 LDT
            'assignment may be scheduled up to 0200 local domicile time',
            # Extension provisions
            'extension procedures',
            'extension shall not cause',
            # Overtime premium conditions
            'overtime premium',
            'circumstances beyond the company',
            # Reserve delay into day off
            'if a reserve pilot departs his domicile and incurs a delay',
        ]
    },
    'extension': {
        'trigger_keywords': ['extension', 'extend', 'extended', 'kept past', 'held over', 'delayed past', 'past midnight', 'past 12', 'after midnight', 'next day', 'gets home', 'got home', '1am', '2am', '3am'],
        'must_include_phrases': [
            'extension procedures',
            'extension shall not cause',
            'overtime premium',
            'a pilot shall not be extended more than one (1) time per month',
        ]
    },
    'junior_assignment': {
        'trigger_keywords': ['junior assignment', 'ja ', 'involuntary assign', 'involuntarily assigned', 'forced in', 'forced to work'],
        'must_include_phrases': [
            'junior assignment',
            'a pilot performing a r-2 rap shall be available for ja at an international location',
            'a pilot who is performing a r-1, r-3 or has been reassigned to an r-4 reserve assignment shall not be eligible to be junior assigned',
            'junior assignment premium',
            'no pilot may be involuntary assigned into a ja prior to forty-eight',
            'a pilot shall not be subject to a ja without his consent when he is on vacation',
            'under no circumstances shall the company involuntary assign a pilot to a ja for more than two (2) independent involuntary assignments in any rolling three (3) month',
        ]
    },
    'fifo': {
        'trigger_keywords': ['fifo', 'first in first out', 'first-in', 'first in, first out', 'who gets called first', 'assignment order', 'who flies first'],
        'must_include_phrases': [
            'first-in, first-out',
            'inverse seniority order',
            'shall rotate back to the bottom',
            'highest positioned reserve pilot on the applicable fifo list',
            'fifo list shall be published by 0900',
        ]
    },
    'reassignment': {
        'trigger_keywords': ['reassign', 'reassignment', 'reroute', 'rerouted', 'moved to different', 'changed trip', 'swap reserve'],
        'must_include_phrases': [
            'reassignment',
            # Reserve reassignment MOU provisions
            'a pilot who has r1 rap',
            'shall not have them reassigned to another type of reserve',
        ]
    },
    'shift_rap': {
        'trigger_keywords': ['shift', 'shifted', 'move my rap', 'change my rap', 'change my dot', 'moved my reserve', 'moved earlier', 'moved later'],
        'must_include_phrases': [
            'shift',
            'four (4) earlier or eight (8) hours later',
            'minimum sixteen (16) hour notice',
            'shall not be shifted into a scheduled day off',
        ]
    },
    'contactability': {
        'trigger_keywords': ['contact', 'contactable', 'phone', 'call back', 'return call', 'missed call', 'answer phone', 'respond to crew scheduling', 'initial call'],
        'must_include_phrases': [
            'must be contactable',
            'return an initial call from crew scheduling within fifteen (15) minutes',
            'contact crew scheduling within thirty (30) minutes',
            'contactable during the entire time of his reserve',
        ]
    },
    'line_construction': {
        'trigger_keywords': ['line construction', 'bid line', 'regular line', 'composite line', 'reserve line', 'domicile flex', 'how lines are built', 'build the schedule', 'monthly bid'],
        'must_include_phrases': [
            'minimum scheduled days off in all constructed initial lines shall be thirteen',
            'shall have at least two (2) separate periods of at least three (3) consecutive days off',
            'no more than seventeen (17) scheduled workdays',
            'all initial lines shall be constructed to be no greater than ninety-five (95) pch',
            'regular line shall be scheduled with at least one (1) day off in any seven',
            'r-3 reserve assignments shall not be scheduled onto regular lines',
            'domicile flex lines shall be built with a minimum, single block of thirteen',
        ]
    },
    'night_flying': {
        'trigger_keywords': ['night trip', 'night flight', 'night flying', 'night pairing', 'red eye', 'stagger', 'no staggering'],
        'must_include_phrases': [
            'no more than four (4) consecutive night trip pairings',
            'no staggering',
            'the company shall schedule all night trip pairings consecutively',
        ]
    },
    'check_airman_admin': {
        'trigger_keywords': ['175%', '175 percent', 'check airman', 'instructor pilot', 'apd', 'administrative assignment', 'admin assignment'],
        'must_include_phrases': [
            'one hundred seventy-five percent (175%)',
            'instructor pilots, check airmen and apd on administrative assignments',
            'if such assignment is on a scheduled day off',
        ]
    },
}

def find_force_include_chunks(question_lower, all_chunks):
    forced = []
    for rule_name, rule in FORCE_INCLUDE_RULES.items():
        if any(kw in question_lower for kw in rule['trigger_keywords']):
            for chunk in all_chunks:
                chunk_text_lower = ' '.join(chunk['text'].lower().split())
                for phrase in rule['must_include_phrases']:
                    if phrase in chunk_text_lower:
                        if chunk not in forced:
                            forced.append(chunk)

# ============================================================
# DEFINITIONS — Contract terms for instant lookup
# ============================================================
DEFINITIONS_LOOKUP = {
    'active service': 'A Pilot who is available for an Assignment, on Sick Leave, Vacation or for any Leaves of Absence where and to the extent that Longevity is accrued for any part of a Month. Periods of Furlough or for Leaves of Absence where Longevity is not accrued, do not constitute Active Service.',
    'agreement': 'This Collective Bargaining Agreement, including any Side Letters to this Agreement; Memorandum of Understanding and Letters of Agreement made contemporaneous with or expressly part of this Collective Bargaining Agreement.',
    'aircraft type': 'A specific make and model aircraft, as defined by the FARs.',
    'assignment': '1) A Flight Assignment, Reserve Period, Training or any other activity that is directed by the Company. 2) An awarded or Assigned Vacancy (Domicile or Position).',
    'block time': 'The time when an aircraft\'s brakes are released for push back or taxi to the time when an aircraft\'s brakes are set at the end of operation.',
    'captain': 'A Pilot who is in command of an aircraft (i.e., Pilot in Command) and is responsible for the manipulation of, or who manipulates the flight controls of an aircraft while under way, including takeoff and landing of such aircraft, and who is properly qualified to serve as, and holds a current airman\'s certificate authorizing service as a Captain and who holds a Captain bid status.',
    'check airman': 'A Pilot who is approved by the Company and the FAA to perform instruction, Training and Checking Events in an aircraft, Simulator or classroom.',
    'composite line': 'A line published as a blank line in the Bid Package. After SAP is completed the Composite Line is constructed by the Company of any combination of Duty and Duty-free times.',
    'daily pay guarantee': 'The minimum pay a Pilot receives for a Day of scheduled Duty or other Company-Directed Assignment. Three and eighty-two hundredths hours (3.82) PCH.',
    'dpg': 'Daily Pay Guarantee. The minimum pay a Pilot receives for a Day of scheduled Duty or other Company-Directed Assignment. Three and eighty-two hundredths hours (3.82) PCH.',
    'day': 'A Calendar Day (00:00-23:59:59) in Local Domicile Time (LDT).',
    'day off': 'A scheduled Day free of all Duty, which is taken at a Pilot\'s Domicile.',
    'deadhead': 'The movement of a Pilot by air or by surface transportation to or from a Flight or other Company-Directed Assignment, as provided in this Agreement.',
    'domicile': 'A Company designated Airport at which Pilots are based regardless of their actual place of Residence. Pilots based at a Domicile shall have their Duty and other Company-Directed Assignments scheduled to begin and end at that Domicile.',
    'domicile flex line': 'A Reserve Line with a minimum single block of thirteen (13) consecutive Days Off for a 30-Day Month and fourteen (14) consecutive Days Off in a 31-Day Month. All Workdays are R-1 Reserve Assignments.',
    'duty': 'An activity Assigned to, scheduled for and/or performed by a Pilot at the direction of the Company. Duty includes Flight Assignments, pre- and post-flight activities, administrative work, Deadhead Transportation, Training, R-1, R-2 or R-4 Reserve, aircraft positioning on the ground, or any other Company-Directed Assignments.',
    'duty period': 'The continuous period of elapsed time beginning at the time when a Pilot is required to Report for Duty or the actual Report Time, whichever is later, until the time when the Pilot is Released from Duty and placed into Rest.',
    'duty rig': 'A method used to calculate pay credits as a ratio of the total Duty Period. The ratio is 1:2: One (1) Pay Credit Hour (PCH) for every two (2) hours of Duty, prorated on a minute for minute basis.',
    'eligible pilot': 'A Pilot who possesses the qualifications to be awarded or Assigned to a Position or to an Assignment.',
    'eligible dependent': 'Spouse, children, domestic partner or other persons who can be claimed for the purposes of coverage or utilization of benefits, tax calculations or other conditions as provided in this Agreement or applicable Law.',
    'extension': 'An Involuntary Assignment to a Flight Segment(s) or other Duty after the last segment of a Pilot\'s originally scheduled Trip Pairing that would not violate the Pilot\'s legality and is within the limitations provided for in Section 14.',
    'fifo': 'First In - First Out Reserve Scheduling. As provided in Section 15 (Reserves), the process for assigning Trip Pairings and other Company-Directed Assignments to Pilot\'s performing Reserve Assignments.',
    'first officer': 'A Pilot who is Second-In-Command of the aircraft. Primary responsibilities are to assist or relieve the Captain in navigation, communication and manipulation of aircraft controls while underway.',
    'flight time': 'The time in hours and minutes from brake release for push back or taxi out until block in.',
    'furlough': 'The voluntary or involuntary removal of a Pilot from Active Service as a Pilot with the Company due to a reduction in force, or the period of time during which such Pilot has Recall rights back to Active Service.',
    'ghost bid': 'A Line that a Full-Time Check Airman or Instructor Pilot has bid for, and as a result of his ineligibility to bid for that Month, he shall not be awarded a Line but shall retain such Initial Line\'s PCH for the purpose of establishing his new MPG for that Month.',
    'grievance': 'A dispute between the Union or Pilot(s) and the Company for alleged Company violation(s) of this Agreement.',
    'junior assignment': 'The procedure used by Crew Scheduling to involuntarily assign a Pilot to Duty on a Day Off, in inverse Seniority Order, beginning with the most junior available Pilot.',
    'ja': 'Junior Assignment. The procedure used by Crew Scheduling to involuntarily assign a Pilot to Duty on a Day Off, in inverse Seniority Order, beginning with the most junior available Pilot.',
    'known flying': 'All Flight Segments known to be performed by the Company prior to the commencement of each Monthly Initial Line Bid Period.',
    'loa': 'Letter of Agreement: An additional addendum to this Agreement, separate from the main body of this Agreement.',
    'mou': 'Memorandum of Understanding.',
    'monthly pay guarantee': 'The minimum PCH value for all published Initial and Final Lines, as provided in Section 3 (Compensation).',
    'mpg': 'Monthly Pay Guarantee. The minimum PCH value for all published Initial and Final Lines.',
    'open time': 'Trip Pairings and Reserve Assignments that remain after the publishing of the Final Bid Awards and any new Trip Pairings or Reserve Assignments that become available during the Month.',
    'pch': 'Pay Credit Hours — the unit of compensation used to calculate pilot pay.',
    'position': 'A Pilot\'s status (Captain or First Officer) on a specific Aircraft Type at a Domicile.',
    'rap': 'Reserve Availability Period. An R-1 or R-2 Assignment in a Pilot\'s Bid Line, or an R-4 Assignment in which a Pilot is obligated to remain available to the Company for the purpose of being Assigned a Trip Pairing or any additional Duty.',
    'regular line': 'A planned sequence of Trip Pairings that also may include Combination Trip Pairings, and a limited number of Reserve Assignments with intervening Days Off.',
    'reserve': 'An Assignment (R-1, R-2, R-3 or R-4) whereby a Pilot is available to be Assigned by the Company to a Trip Pairing or other Company-Directed Assignment.',
    'rest period': 'A specific period of time, free from all Duty or other Company-Directed Assignments, between such Assignment and his next scheduled Company-Directed Assignment or between an Assignment and a Layover Period.',
    'sap': 'Schedule Adjustment Period. As provided in Section 14 (Scheduling) the process during the Monthly Bid Period where a Pilot may modify his Initial Line Award after the Integration procedure through Pick-Up and Trade transactions.',
    'seniority': 'A Pilot\'s relative position on the NAC System Seniority List, based on his length of service with the Company, starting on his Date of Hire.',
    'trip pairing': 'A Trip Pairing shall consist of one (1) or more Duty Periods and contain any mixture of Flight and/or Deadhead Segments. Beginning and ending at a Pilot\'s Domicile.',
    'trip rig': 'Pay credit based on elapsed trip time. Time Away From Domicile (TAFD) divided by 4.9.',
    'tdy': 'Temporary Duty Vacancy. A temporary Assignment whereby a Pilot may bid and be awarded to a location other than the Pilot\'s Domicile.',
    'vacancy': 'An open Position (Domicile/Aircraft Type/Status) to be filled per Section 18.',
}

# ============================================================
# TIER 1 RULES — Fixed-value instant answers (no API call)
# ============================================================
TIER1_RULES = {
    'grievance_deadline': {
        'keywords': ['grievance deadline', 'grievance time limit', 'how long to file a grievance',
                     'how long do i have to file', 'how long to grieve', 'grievance filing deadline',
                     'time to file grievance', 'when to file grievance', 'deadline to grieve',
                     'days to file grievance', 'days to grieve'],
        'answer': """📄 CONTRACT LANGUAGE: "A Pilot or Union Representative must first attempt to resolve the dispute informally with the Chief Pilot, or designee, via phone conversation, personal meeting, or e-mail within thirty (30) Days after the Pilot became aware, or reasonably should have become aware, of the event giving rise to the Grievance."
📍 Section 19.C.1, Page 220

"If the dispute is not resolved during the informal discussion, the Pilot or Union may file a written Grievance within twenty (20) Business Days after the informal discussion."
📍 Section 19.C.2, Page 220

"Failure to file or advance any Grievance within the time periods prescribed in this Section shall result in the waiver and abandonment of the Grievance."
📍 Section 19.D.2, Page 222

📝 EXPLANATION: The contract establishes a two-step filing process:
- Step 1: Attempt informal resolution within 30 Days of becoming aware of the event (Section 19.C.1)
- Step 2: If unresolved, file a written Grievance within 20 Business Days after the informal discussion (Section 19.C.2)
- Missing either deadline results in waiver and abandonment of the Grievance (Section 19.D.2)

Full timeline: 30 Days (informal) → 20 Business Days (written filing) → 10 Business Days (meeting) → 10 Business Days (Company decision) → 20 Business Days (appeal to System Board)

🔵 STATUS: CLEAR - The contract explicitly states these deadlines in Sections 19.C and 19.D.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.""",
    },

    'minimum_days_off': {
        'keywords': ['minimum days off', 'how many days off', 'days off per month',
                     'min days off', 'days off minimum', 'monthly days off',
                     'how many days off per month', 'days off in a month'],
        'answer': """📄 CONTRACT LANGUAGE: "The minimum scheduled Days Off in all constructed Initial Lines shall be thirteen (13) in a thirty (30) Day Month and fourteen (14) in a thirty-one (31) Day Month."
📍 Section 14.E.2.d (LOA #15), Page 328

"All Regular, Composite, Reserve, and Domicile Flex Lines shall have either two (2) separate periods of at least three (3) consecutive Days Off, or one single block of at least five (5) consecutive Days Off."
📍 Section 14.E.2.b (LOA #15), Page 328

📝 EXPLANATION: Per the contract, the minimum Days Off per month are:
- 30-day month: 13 Days Off minimum
- 31-day month: 14 Days Off minimum

These minimums apply to all line types (Regular, Composite, Reserve, Domicile Flex). Additionally, Days Off must be structured as either two blocks of 3+ consecutive Days Off, or one block of 5+ consecutive Days Off.

Exception: TDY Lines have reduced minimums — 12 Days Off (30-day month) or 13 Days Off (31-day month) per Section 14.E.3.d.

🔵 STATUS: CLEAR - The contract explicitly states minimum Days Off in Section 14.E.2.d (LOA #15).


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.""",
    },

    'dpg_value': {
        'keywords': ['what is the dpg', 'what is dpg', 'dpg value', 'dpg amount',
                     'how much is dpg', 'daily pay guarantee amount', 'daily pay guarantee value',
                     'what is the daily pay guarantee', 'dpg pch', 'dpg hours'],
        'answer': """📄 CONTRACT LANGUAGE: "Daily Pay Guarantee (DPG): Three and eighty-two hundredths hours (3.82) PCH."
📍 Section 2 (Definitions), Page 21

"A Pilot who is scheduled for Reserve or performs an Assignment while on Reserve shall be paid the greater of: (a) the applicable Daily Pay Guarantee; or (b) the PCH earned from the assigned Trip Pairing."
📍 Section 3.F.1.b, Page 53

📝 EXPLANATION: The Daily Pay Guarantee (DPG) is 3.82 PCH per day of scheduled Duty or Company-Directed Assignment. This is the minimum a pilot receives for any workday, regardless of actual block time. The pilot always receives the GREATER of DPG, block time, Duty Rig, or Trip Rig.

To calculate the dollar value: 3.82 PCH x your current hourly rate. For example, a Year 12 B737 Captain (217.33/hour): 3.82 x 217.33 = 830.20 per day minimum.

🔵 STATUS: CLEAR - The contract explicitly defines DPG as 3.82 PCH in Section 2.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.""",
    },

    'rest_minimums': {
        'keywords': ['minimum rest', 'rest requirement', 'how much rest', 'rest between',
                     'rest minimum', 'min rest', 'hours of rest', 'rest after duty',
                     'rest period requirement', 'required rest'],
        'answer': """📄 CONTRACT LANGUAGE: "A Pilot shall be given a minimum Rest Period of ten (10) consecutive hours after completing a Duty Period of fourteen (14) hours or less."
📍 Section 13.G.1, Page 155

"A Pilot shall be given a minimum Rest Period of twelve (12) consecutive hours after completing a Duty Period of more than fourteen (14) hours."
📍 Section 13.G.1, Page 155

"If a Pilot's Rest is interrupted, the required Rest Period begins anew."
📍 Section 13.H.7, Page 156

📝 EXPLANATION: Per the contract, minimum rest requirements are:
- After duty of 14 hours or less: 10 hours minimum rest
- After duty of more than 14 hours: 12 hours minimum rest

Important: If rest is interrupted (phone calls, hotel disturbances, etc.), the full rest period starts over from the beginning per Section 13.H.7. Only emergency or security notifications are exempt.

Note: A Rest Period is NOT the same as a Day Off. A Day Off is a full calendar day (00:00-23:59) free from all Duty at Domicile.

🔵 STATUS: CLEAR - The contract explicitly states rest minimums in Section 13.G.1.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.""",
    },

    'duty_time_limits': {
        'keywords': ['duty time limit', 'maximum duty', 'max duty', 'duty limit',
                     'how long can i be on duty', 'duty hour limit', 'max duty hours',
                     'maximum duty time', 'duty time max', 'how many hours of duty',
                     'duty hours limit', 'longest duty day'],
        'answer': """📄 CONTRACT LANGUAGE: "No Pilot shall be scheduled for or required to exceed the following maximum Duty Time limitations..."
📍 Section 13.F.1, Page 154

📝 EXPLANATION: Per the contract, maximum duty time depends on crew complement:
- Basic crew (2 pilots): 16 hours maximum
- Augmented crew (3 pilots): 18 hours maximum
- Heavy crew (4 pilots): 20 hours maximum

Per Section 14.N, if duty is projected to exceed these limits, the Company must remove the pilot from the trip and place them into rest. A pilot may not be extended beyond these limits.

Per Section 13.F, these are hard limits — not targets. Scheduled duty should be planned well within these maximums.

🔵 STATUS: CLEAR - The contract explicitly states duty time limits in Section 13.F.1.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.""",
    },

    'ja_limits': {
        'keywords': ['ja limit', 'junior assignment limit', 'how many ja', 'how many junior assignment',
                     'ja per month', 'ja in 3 months', 'ja rolling', 'max ja',
                     'maximum junior assignment', 'ja frequency', 'how often can i be ja'],
        'answer': """📄 CONTRACT LANGUAGE: "Under no circumstances shall the Company involuntary assign a Pilot to a JA for more than two (2) independent involuntary assignments in any rolling three (3) Month period."
📍 Section 14.O, Page 188

"A Pilot shall not be subject to a JA without his consent when he is on Vacation."
📍 Section 14.O, Page 188

"No Pilot may be involuntary assigned into a JA prior to forty-eight (48) hours before the scheduled departure time."
📍 Section 14.O, Page 188

📝 EXPLANATION: Per the contract, Junior Assignment limits are:
- Maximum 2 involuntary JAs in any rolling 3-month period
- Cannot be junior assigned while on Vacation
- Cannot be junior assigned more than 48 hours before departure
- JA must follow inverse seniority order (most junior pilot first)
- JA Premium: 200% for 1st JA in rolling 3 months, 250% for 2nd JA (Section 3.R)
- R-1, R-3, and R-4 pilots are NOT eligible for JA (Section 14.O.14)
- R-2 pilots are eligible for JA at international locations ONLY (Section 14.O.14)

🔵 STATUS: CLEAR - The contract explicitly states JA limits in Section 14.O.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.""",
    },

    'extension_limits': {
        'keywords': ['extension limit', 'how many extensions', 'extension per month',
                     'max extensions', 'maximum extensions', 'extensions per month',
                     'how often can i be extended', 'extension frequency', 'extension rules'],
        'answer': """📄 CONTRACT LANGUAGE: "A Pilot shall not be extended more than one (1) time per Month."
📍 Section 14.N.6, Page 186

"An Extension shall not cause a Pilot to exceed the applicable Duty Time limitations of Section 13."
📍 Section 14.N, Page 185

📝 EXPLANATION: Per the contract, Extension limits are:
- Maximum 1 involuntary extension per calendar month (Section 14.N.6)
- Extensions cannot exceed duty time limits (16hr/18hr/20hr per Section 13.F)
- Extensions cannot cause a pilot to miss a scheduled Day Off beyond 0200 LDT (Section 15.A.7)
- An Extension is defined as an involuntary assignment to additional duty after the last segment of a pilot's originally scheduled Trip Pairing

If you have been extended more than once in a month, this is a potential contract violation.

🔵 STATUS: CLEAR - The contract explicitly states the one-extension-per-month limit in Section 14.N.6.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.""",
    },
}

# ============================================================
# QUICK REFERENCE CARDS — Hand-written reference content
# ============================================================
QUICK_REFERENCE_CARDS = {
    "What is a Pay Discrepancy?": {
        "icon": "💰",
        "content": """## What is a Pay Discrepancy?

A pay discrepancy occurs when your actual pay does not match what the contract says you should receive. Common examples:

**Daily Pay Guarantee (DPG) Issues**
- You were on duty but received less than 3.82 PCH for that workday
- DPG was not applied when it should have been

**Duty Rig Shortfalls**
- Your duty day was long but you were only paid for block time
- Duty Rig calculation: 1 PCH for every 2 hours on duty (1:2 ratio)
- You should receive the GREATER of block time, DPG, or Duty Rig

**Trip Rig (TAFD) Issues**
- Time Away From Domicile was not calculated correctly
- Trip Rig: Total TAFD hours ÷ 4.9

**Overtime / Premium Pay**
- Open Time Premium not applied (1.5x rate)
- Junior Assignment Premium missing
- Check Airman/Instructor/APD Day Off administrative pay (175%) not applied (Section 3.S.5.b)

**Rate Issues**
- Wrong longevity year applied
- Annual 2% increase not reflected (per Section 3.B.3)
- Wrong position rate (Captain vs First Officer)

**What To Do:**
1. Compare your pay stub to your actual schedule and duty times
2. Calculate what you believe you are owed using the contract formulas
3. Contact your union representative with your documentation
4. File a pay grievance if the discrepancy is confirmed"""
    },

    "Reserve Types & Definitions": {
        "icon": "🔄",
        "content": """## Reserve Types & Definitions
*Per Section 15 of the JCBA (Pages 190-200)*

Reserve Assignments consist of four types (15.B.1): R-1, R-2, R-3, and R-4. The Company determines the number and types each Monthly Bid Period.

---

**R-1: Domicile Short Call Reserve (Section 15.B.2)**
- R-1 is **Duty** (15.B.2.a)
- Applies to **In-Domicile** reserve obligations only (15.B.2.b)
- Scheduled DOT and Duty Off times published in Monthly Bid Package and constructed into Lines (15.B.2.c)
- DOT and Duty Off may be scheduled differently from Day to Day (14.E.13.d)
- **Max RAP duration: 12 hours** (15.A.3)
- Must return Initial Call within **15 minutes** (15.A.8)
- When assigned a trip: not required to report prior to **2 hours** after Initial Contact (15.B.2.d)
- Crew Scheduling may shift RAP up to **4 hours earlier or 8 hours later** than scheduled DOT (15.A.11); minimum **16-hour notice** required (15.A.11.d)
- RAP shall not be shifted into a scheduled Day Off (15.A.11.b)
- First RAP in a block shall not be shifted earlier; last RAP in a block shall not be shifted later (15.A.11.a)
- R-1 RAPs **shall not be Reassigned** to another type of Reserve Assignment (MOU, Page 384)
- **NOT eligible for Junior Assignment** (14.O.14)
- On the FIFO List for trip assignment (15.C.1.a)

**R-2: Out-of-Domicile Short Call Reserve (Section 15.B.3)**
- R-2 is **Duty** (15.B.3.b)
- Applies to **Out-of-Domicile** reserve obligations (15.B.3.a)
- Pilot shall be notified at least **10 hours** prior to next R-2 RAP DOT (15.B.3.c)
- **Max RAP duration: 12 hours** (15.A.3)
- Must return Initial Call within **15 minutes** (15.A.8)
- When assigned a trip: must report within **1 hour** of Initial Call; or be available for Company transportation within **1 hour** of Initial Contact (15.B.3.d)
- Must receive at least one **24-hour Rest Period** free from all Duty within any **7 consecutive days** (15.B.3.e)
- Crew Scheduling may shift RAP up to **4 hours earlier or 8 hours later** (15.A.11); minimum **16-hour notice** (15.A.11.d)
- When R-2 RAPs are scheduled in blocks, a minimum of **5 consecutive Days Off** in Domicile shall follow each block (14.E.13.g)
- R-2 Lines shall be constructed with **purely R-2 RAPs**, except when an R-2 RAP is scheduled within a Trip Pairing (14.E.13.c)
- May be Reassigned from **any location** to cover unassigned flying when no R-1 is available (15.C.2.a.(2))
- **Eligible for Junior Assignment at International locations ONLY** (14.O.14)
- On the FIFO List for trip assignment (15.C.1.a)

**R-3: Long Call Reserve (Section 15.B.4)**
- **No Duty Time Limitations** while performing R-3; once assigned a trip, Section 13 (Hours of Service) applies (15.B.4.a)
- Scheduled **0000-2359 Local Time**, except when in Rest or released (15.B.4.b)
- Must advise Crew Scheduling of **Residence Airport** prior to beginning of that Month (15.B.4.c); Residence Airport must be near Primary Residence with more than one FAR Part 121 carrier serving it
- Must contact Crew Scheduling within **30 minutes** of Initial Call (15.B.4.h.(4))
- Contactable via personal phone with voicemail OR Company-approved PCD (15.B.4.h)
- When assigned a trip **NOT at Domicile**: put into Rest, minimum **12 hours** to report; Duty begins 1 hour before scheduled departure; **Company pays airfare** (15.B.4.e)
- When assigned a trip **at Domicile**: pilot responsible for own travel and costs; Duty On no earlier than **12 hours** from Initial Call (15.B.4.f)
- Must receive at least one **24-hour Rest Period** free from all Duty within any **7 consecutive days** (15.B.4.i)
- R-3 shall **NOT be scheduled onto Regular Lines** (14.E.5.g)
- **NOT eligible for Junior Assignment** (14.O.14)
- **NOT on the R-1/R-2 FIFO List** (15.C.1.a — FIFO Lists consist of R-1 and R-2 only)

**R-4: Airport Reserve (Section 15.B.5)**
- R-4 is **Duty** (15.B.5.b)
- Performed at Pilot's **Domicile or another designated Airport/location** selected by the Company (15.B.5.a)
- A Pilot on R-1 or R-2 **may be Reassigned** to R-4 (15.B.5.c)
- When Reassigned **before** RAP DOT: R-4 shall not exceed **4 consecutive hours**; if not assigned a trip, released from all Duty for that Day (15.B.5.c)
- When Reassigned **during** an R-1 or R-2 RAP: must report to airport per R-1 (15.B.2.d) or R-2 (15.B.3.d) rules; R-4 shall not exceed **4 hours**; if not assigned, released for the Day (15.B.5.d)
- **NOT eligible for Junior Assignment** (14.O.14)

---

**FIFO — First In, First Out (Section 15.C)**
- Separate FIFO Lists for each **Position and Domicile**, consisting of **R-1 and R-2 Pilots only** (15.C.1.a)
- Lists sorted in **numerical order** (15.C.1.a)
- Initial placement: **inverse Seniority Order** — most junior Pilot is first (top) on list (15.C.1.b.(1))
- Single-Day Reserve Pilots placed on FIFO in same manner for each Reserve Day (15.C.1.b.(1))
- After completing an assignment: rotates to **bottom** of FIFO List (15.C.1.b.(2))
- When two Pilots have same Duty Off Time: more **junior** Pilot is higher on FIFO (15.C.1.b.(3))
- When Deadheading Pilot and Flying Pilot have same Duty Off Time: **Flying Pilot** is higher (15.C.1.b.(4))
- Pilot stays at top of FIFO until: assigned and reports for duty, has a Day Off, or changes FIFO List (15.C.1.c)
- Each time a Pilot returns from a **Day Off**: goes to **bottom** of FIFO List (15.C.1.d)
- Assignments go to **highest positioned** Pilot who is legal to accept (15.C.2)
- FIFO Lists published by **0900 LDT each Day**, updated within **1 hour** of each change, showing through next Day (15.C.1.e)
- All FIFO Lists available on **Company Intranet** (15.C.1.e)

---

**General Reserve Rules (Section 15.A)**
- Reserve covers unanticipated absences: illness, fatigue, emergency leave, charters, ferry flights, IROP, route changes, Open Time (15.A.1)
- Pilot may request release from RAP within **4 hours** of Duty Off Time if not assigned (15.A.4)
- If not assigned within **2 hours** of Duty Off Time: **automatically released** (15.A.4)
- Assignment shall **not conflict** with a scheduled Day Off, except may be scheduled up to **0200 LDT** into a Day Off (15.A.7-8)
- Upon completing an assignment, Reserve Pilot **immediately goes into Rest** before next assignment (15.A.10)
- If delay causes work into Day Off, **Extension provisions** in Section 14 control (15.A.9)
- Reserve pay per **Section 3 (Compensation)** (15.E)

---

**Contactability (Section 15.D)**
- Must be contactable during **entire time** of Reserve (15.D.2)
- Contact methods: personal phone with voicemail; when on R-2, hotel/lodging number; Company-approved PCD (15.D.1)
- Must ensure Crew Scheduling has **accurate contact info**; inform of changes before next DOT (15.D.3)

**Key Definitions:**
- **RAP** = Reserve Availability Period (the hours you must be available)
- **DOT** = Duty On Time
- **Day Off** = A scheduled day free of ALL Duty at Domicile (00:00-23:59 Local) — this is a defined term
- **Rest Period** = Minimum consecutive hours free from Duty between assignments — NOT the same as a Day Off
- **Initial Call** = First contact from Crew Scheduling for an assignment
- **Positive Contact** = Direct communication confirmed between Pilot and Crew Scheduling (phone, text, or email)

⚠️ *Also see MOU on Reserve Reassignment (Pages 383-385) for rules on reassignment between reserve types.*"""
    },

    "Minimum Days Off / Availability": {
        "icon": "📅",
        "content": """## Minimum Days Off, Scheduling & Line Construction Rules
*Per Section 14.E (LOA #15, Pages 326-349) and Section 15 of the JCBA*

---

### LINE CONSTRUCTION PARAMETERS (14.E.2)

**Maximum Scheduled Workdays Per Month (14.E.2.c)**
- All Lines (Regular, Composite, Reserve, Domicile Flex): **17 Workdays max**
- TDY Lines: **18 Workdays max** (including Deadhead to/from TDY location) (14.E.3)

**Minimum Monthly Days Off (14.E.2.d)**
- **30-day month: 13 Days Off minimum**
- **31-day month: 14 Days Off minimum**
- Applies to ALL line types (Regular, Composite, Reserve, Domicile Flex)
- TDY Lines: **12 Days Off** (30-day month), **13 Days Off** (31-day month) (14.E.3.d)

**Days Off Structure (14.E.2.b)**
All Regular, Composite, Reserve, and Domicile Flex Lines must have EITHER:
- Two (2) separate periods of at least **3 consecutive Days Off**, OR
- One single block of at least **5 consecutive Days Off**

**All scheduled Days Off** in published Initial and Final Line awards shall be scheduled **in the Pilot's Domicile** (14.E.2.e)

**Maximum Line Value: 95 PCH** — no Line shall exceed this (14.E.2.f)

---

### WEEKLY MINIMUMS (1 Day Off / Rest Period per 7 Days)

| Line Type | Requirement | Citation |
|-----------|-------------|----------|
| Regular Line | At least 1 Day Off in any 7 consecutive days | 14.E.5.a (LOA #15) |
| Composite Line | At least 1 Day Off in any 7 consecutive days | 14.E.7.d (LOA #15) |
| Reserve (R-2) | At least one 24-hour Rest Period free from all Duty within any 7 consecutive days | 15.B.3.e |
| Reserve (R-3) | At least one 24-hour Rest Period free from all Duty within any 7 consecutive days | 15.B.4.i |
| Domicile Flex Line | A scheduled consecutive 24-hour period free from all Duty within a 7 consecutive Day period | 14.E.9.h (LOA #15) |
| Training (15+ days) | At least 1 Day Off during every 7 consecutive days of Training; no more than 5 consecutive days with scheduled Simulator Periods | 12.G.g |

---

### LINE-SPECIFIC CONSTRUCTION RULES

**Regular Lines (14.E.5, LOA #15)**
- Company shall construct **maximum number** of Regular Lines per Position (14.E.5.a)
- Regular Lines constructed **first** from Known Flying, with highest PCH Trip Pairings (14.E.2.g)
- A planned sequence of Trip Pairings, with or without a **limited number of R-1 or R-2 RAPs** (max 6 RAPs) (14.E.5.b)
- "Pure Lines" (Trip Pairings only) shall be constructed to the extent possible (14.E.5.b)
- All Days Off shall be at **Domicile** (14.E.5.c)
- All Trip Pairings shall **begin and end at Domicile** (14.E.5.d)
- To the extent possible, **no single Days Off** during the Month, except first or last Day (14.E.5.e)
- Consistent weekly work patterns and report times to the extent possible (14.E.5.f)
- R-3 shall **NOT** be scheduled onto Regular Lines (14.E.5.g)
- Night Trip Pairings scheduled **consecutively**; max **4 consecutive** Night Trips without 2 Days Off; **no staggering** (14.E.5.g/h)

**Composite Lines (14.E.7, LOA #15)**
- Blank when published; constructed **after SAP** (14.E.7.a)
- Combination of: Trip Pairings, Reserve Duty, Vacation, Training, Company-Directed Assignments, Days Off (14.E.7.c)
- At least 1 Day Off in any 7 consecutive Days (14.E.7.d)
- No less than Minimum Days Off in a Month (14.E.7.e)
- To the extent possible, **at least 2 Days Off** shall separate blocks of Trip Pairings (14.E.7.f)

**Reserve Lines (14.E.8, LOA #15)**
- Shall contain **only Reserve Assignments** (14.E.8.a)
- Types: R-1 RAP, R-2 RAP, R-3 (14.E.8.a)
- To the extent possible, each Reserve Line built with **only one type** (R-1 only or R-3 only); may mix R-1 and R-3 blocks if each block is same type (14.E.8.b)
- R-2 Lines: **purely R-2 RAPs** except when R-2 is within a Trip Pairing (14.E.8.c)
- Single-Day Reserve limited to **first or last Day** of Month (14.E.8.f)
- R-2 blocks: minimum **5 consecutive Days Off** in Domicile after each block (14.E.8.g)

**Domicile Flex Lines (14.E.9, LOA #15)**
- Minimum single block of **13 consecutive Days Off** (30-day month) or **14 consecutive Days Off** (31-day month) (14.E.9.b)
- All Workdays shall be **R-1 Reserve Assignments** (14.E.9.c)
- Created from Reserve Lines: if 3+ Reserve Lines are constructed, **50%** (rounded up) shall be Domicile Flex Lines for requesting Pilots (14.E.2.j)
- Minimum rest: scheduled consecutive **24-hour period** free from all Duty within 7 Days (14.E.9.h)
- Pilots must **request** a Domicile Flex Line during Training Bid Period (14.E.9.d)

**TDY Lines (14.E.3, LOA #15)**
- Max **18 Workdays** per Month (14.E.3.c)
- Min Days Off: **12** (30-day month), **13** (31-day month) (14.E.3.d)
- All Workdays scheduled **consecutively** (14.E.3.a via original 14.E.4)
- Days Off scheduled inside a consecutive block of TDY Workdays are **NOT considered a Day Off** for minimum Days Off purposes (14.E.3, original 14.E.5)
- At least 50% of TDY Lines begin and end in same Month (14.E.3.e)

---

### TRAINING DAYS OFF (Section 12.G)
- Training of **15+ days**: at least **1 Day Off** during every 7 consecutive days (12.G.g)
- No more than **5 consecutive days** with scheduled Simulator Periods without a Day Off (12.G.g)
- After completing Initial, Upgrade, or Transition Training: at least **2 Days** free of Duty at Domicile (unless Pilot agrees otherwise) (12.G.f)

---

### KEY DEFINITIONS
- **Day Off** = A scheduled day free of ALL Duty at Domicile (00:00-23:59 Local) — this is a defined term
- **Rest Period** = Minimum consecutive hours free from Duty between assignments — NOT a Day Off
- **Workday** = A Day with scheduled Duty or Company-Directed Assignment
- **MPG** = Monthly Pay Guarantee
- **Known Flying** = All flight segments known at the start of the Monthly Bid Period

⚠️ *Refer to LOA #15 (Pages 320-349) which supersedes original Section 14.E provisions. Also see Section 13 (Hours of Service) for Duty Time and Rest requirements.*"""
    },

    "Pay Calculation Guide": {
        "icon": "🧮",
        "content": """## Pay Calculation Guide — The 4-Way Comparison
*Per Section 3.E of the JCBA (Pages 52-53)*

Every trip or duty day, you are paid the **GREATER** of four calculations. The Company must pay whichever is highest.

---

**1. Block Time PCH**
Your actual flight time (brake release to block in).
- Example: 6.0 hours of flying = 6.0 PCH

**2. Duty Rig (1:2 ratio)**
One PCH for every two hours of total Duty Time, prorated minute-by-minute.
- Formula: Total Duty Hours ÷ 2
- Example: 12 hours duty = 6.0 PCH

**3. Daily Pay Guarantee (DPG)**
Minimum pay per workday: **3.82 PCH per day**
- For multi-day trips, multiply by number of days
- Example: 3-day trip = 3.82 × 3 = 11.46 PCH

**4. Trip Rig (TAFD ÷ 4.9)**
Time Away From Domicile divided by 4.9, prorated minute-by-minute.
- Formula: Total TAFD Hours ÷ 4.9
- Example: 40 hours TAFD = 8.16 PCH
- Only applies to multi-day trips (not single duty periods)

---

**Example Calculation:**
A 3-day trip with 12 hours block, 28 hours duty, 38 hours TAFD:
| Method | Calculation | PCH |
|--------|-------------|-----|
| Block Time | 12.0 hours | 12.0 |
| Duty Rig | 28 ÷ 2 | 14.0 |
| DPG | 3.82 × 3 days | 11.46 |
| Trip Rig | 38 ÷ 4.9 | 7.76 |

**Winner: Duty Rig at 14.0 PCH** → 14.0 × your hourly rate = trip pay

---

**Premium Multipliers (applied AFTER the 4-way comparison):**
| Situation | Premium | Section |
|-----------|---------|---------|
| Open Time pickup | 150% | 3.N |
| Day Off duty (weather/mx/ATC) | 150% | 3.Q.1 |
| Junior Assignment (1st in 3 months) | 200% | 3.R.1 |
| Junior Assignment (2nd in 3 months) | 250% | 3.R.2 |
| Check Airman Day Off admin | 175% | 3.S.5.b |

**Current Hourly Rate = DOS Rate × 1.02^(years since July 2018)** — rates increase 2% annually per Section 3.B.3

⚠️ Always verify your pay stub matches the highest of the four calculations."""
    },

    "Extension Rules": {
        "icon": "⏰",
        "content": """## Extension Rules
*Per Section 14.N of the JCBA (Pages 185-186)*

An Extension is an involuntary assignment to additional duty after your originally scheduled Trip Pairing.

---

**Hard Limits:**
- **1 extension per month maximum** (Section 14.N.6)
- Extensions **cannot exceed duty time limits** (16hr basic / 18hr augmented / 20hr heavy crew per Section 13.F)
- Extensions **cannot cause you to miss a Day Off** beyond 0200 LDT (Section 15.A.7)

**Your Rights When Extended:**
- You must be notified before your last flight segment departs (Section 14.K.1)
- Extension must not violate your legality (rest, duty limits)
- If you've already been extended once this month, you **cannot** be extended again

**Pay for Extensions:**
- **150% overtime premium** applies to all duty performed during the extension (Section 14.K.2.i / Section 3.Q)
- Pay is calculated using the same 4-way comparison (Block, Duty Rig, DPG, Trip Rig) — whichever is greater
- The overtime premium applies to the PCH earned

**Mechanical Delay During Extension:**
- If delayed beyond 3 hours after original Duty Off Time due to circumstances beyond Company control (weather, mx, ATC), you finish the trip (Section 14.K.1.h)
- Company must provide hotel and transportation if needed

**What to Track:**
- ✅ Time of extension notification
- ✅ Your original scheduled Duty Off time
- ✅ Whether this is your 1st or 2nd extension this month
- ✅ Total duty time (to verify limits aren't exceeded)
- ✅ Whether duty extends into a scheduled Day Off

⚠️ **If you've been extended more than once in a calendar month, contact your union representative immediately — this is a potential contract violation.**"""
    },

    "Junior Assignment Rules": {
        "icon": "⚖️",
        "content": """## Junior Assignment (JA) Rules
*Per Section 14.O of the JCBA (Pages 188-190) and Section 3.R (Pages 61-62)*

A Junior Assignment is when the Company involuntarily assigns a pilot to duty on a Day Off.

---

**Hard Limits:**
- **Maximum 2 JAs in any rolling 3-month period** (Section 14.O.12)
- Cannot be JA'd while on **Vacation** (Section 14.O)
- Cannot be JA'd more than **48 hours** before departure (Section 14.O)
- Must follow **inverse seniority order** — most junior available pilot first (Section 14.O.4)

**Who Can Be JA'd:**

| Reserve Type | JA Eligible? | Notes |
|-------------|-------------|-------|
| R-1 | ❌ No | Section 14.O.14 |
| R-2 | ⚠️ International only | Section 14.O.14 |
| R-3 | ❌ No | Section 14.O.14 |
| R-4 | ❌ No | Reassigned, not eligible |
| Line holders | ✅ Yes | On Day Off, inverse seniority |

**JA Pay Premiums:**

| Situation | Premium | Section |
|-----------|---------|---------|
| 1st JA in rolling 3 months | **200%** of hourly rate | 3.R.1 |
| 2nd JA in rolling 3 months | **250%** of hourly rate | 3.R.2 |

Premium applies to ALL PCH earned during the JA, paid **in addition** to monthly pay (Section 3.R.3).

**Example:** Year 8 Captain, 10-hour duty day, 1st JA in 3 months:
- Duty Rig: 10 ÷ 2 = 5.0 PCH (highest of 4-way comparison)
- JA Premium: 5.0 × 191.22 × 200% = 1,912.20

**What to Track:**
- ✅ Date/time of JA notification
- ✅ Was inverse seniority followed? (Were more junior pilots available?)
- ✅ Is this your 1st or 2nd JA in the rolling 3-month period?
- ✅ Were you on a scheduled Day Off?
- ✅ Total duty time and block time for pay calculation

⚠️ **If you've been JA'd 3 times in 3 months, or JA'd on Vacation, contact your union representative immediately.**"""
    },

    "Open Time & Trip Pickup": {
        "icon": "✈️",
        "content": """## Open Time & Trip Pickup
*Per Section 14.M-N of the JCBA (Pages 183-186)*

Open Time consists of Trip Pairings and Reserve Assignments remaining after Final Bid Awards, plus any new trips that become available during the month.

---

**How to Pick Up Open Time:**
1. Open Time is posted on the Company's system
2. Pilots may request to pick up available trips during SAP (Schedule Adjustment Period) or during the month
3. Awards are based on **seniority** — most senior requesting pilot gets the trip

**Open Time Premium Pay:**
- **150% of applicable hourly rate** for all PCH earned (Section 3.N)
- This is a significant pay boost — always check what's available
- Premium applies to the GREATER of the 4-way pay comparison (Block, Duty Rig, DPG, Trip Rig)

**Example:** Year 8 Captain picks up a trip with 8.0 PCH:
- 8.0 × 191.22 × 150% = 2,294.64

**SAP (Schedule Adjustment Period):**
- Occurs after Initial Line Awards are published (Section 14.H)
- Pilots can pick up trips, trade trips, or drop trips during SAP
- Seniority-based awards

**Trip Trading:**
- Pilots may trade trips with other pilots (Section 14.L)
- Both pilots must be legal for the other's trip
- Trades must not create conflicts with existing schedule

**Key Restrictions:**
- Cannot pick up Open Time that conflicts with scheduled assignments
- Cannot exceed duty time limits or violate rest requirements
- Must maintain minimum Days Off requirements
- Company may restrict pickups to maintain operational coverage

**What to Track:**
- ✅ Open Time posting times
- ✅ Your pickup requests and timestamps
- ✅ Whether seniority order was followed in awards
- ✅ PCH earned vs. what shows on pay stub (verify 150% applied)

⚠️ **Open Time at 150% is one of the best ways to increase your monthly pay. Check the board regularly.**"""
    },

    "How to File a Grievance": {
        "icon": "📋",
        "content": """## How to File a Non-Disciplinary Grievance
*Per Section 19.C of the JCBA (Pages 220-222)*

There are two types of Grievances: Disciplinary (Section 19.B) and Non-Disciplinary (Section 19.C). Below is the Non-Disciplinary process — the most common type for pay, scheduling, and contract interpretation disputes.

**Step 1: Attempt Informal Resolution — DEADLINE: 30 Days**
Per Section 19.C.1: You or a Union Representative must first attempt to resolve the dispute informally with the Chief Pilot, or designee, via phone conversation, personal meeting, or email within **30 Days** after you became aware, or reasonably should have become aware, of the event.

**Step 2: File a Written Grievance — DEADLINE: 20 Business Days after Step 1**
Per Section 19.C.2: If not resolved informally, you or the Union may file a written Grievance within **20 Business Days** after the informal discussion. Per Section 19.C.2, the written request must include:
- A statement of the known facts
- The specific sections of the Agreement allegedly violated
- The dates out of which the Grievance arose
- A request for relief (what remedy you are seeking)

File this with the **Director of Operations, or designee** (Section 19.C.2).

**Step 3: Grievance Meeting — Within 10 Business Days**
Per Section 19.C.3: A Grievance Meeting between the Grievant, Union, and Director of Operations (or designee) shall be held within **10 Business Days** after receipt of your written request. The meeting is telephonic unless the parties mutually agree to meet in person.

**Step 4: Exchange Documents — At Least 1 Business Day Before Meeting**
Per Section 19.C.4-5: Both sides must provide copies of any documents, witness statements, and records of how the Company has interpreted or applied the provision in dispute. Documents must be exchanged **at least 1 Business Day** before the Grievance Meeting.

**Step 5: Company Decision — Within 10 Business Days After Meeting**
Per Section 19.C.7: The Director of Operations, or designee, shall issue a **written decision** (including any relief granted) to you and the Union within **10 Business Days** after the Grievance Meeting.

**Step 6: Appeal to System Board — DEADLINE: 20 Business Days**
Per Section 19.B.20 / Section 20: If you or the Union are not satisfied with the Company's decision, the Union may make a **written appeal** to the NAC Pilots System Board of Adjustment within **20 Business Days** after receipt of the decision.

---

**⏰ CRITICAL DEADLINES — Missing any deadline forfeits your Grievance:**

| Step | Action | Deadline |
|------|--------|----------|
| 1 | Informal resolution attempt | 30 Days from awareness |
| 2 | File written Grievance | 20 Business Days after Step 1 |
| 3 | Grievance Meeting held | 10 Business Days after filing |
| 4 | Document exchange | 1 Business Day before meeting |
| 5 | Company written decision | 10 Business Days after meeting |
| 6 | Appeal to System Board | 20 Business Days after decision |

Per Section 19.D.1: Time limits may be extended by **written agreement** between Company and Grievant or Union.

Per Section 19.D.2: **Failure to file or advance any Grievance within the time periods prescribed shall result in the waiver and abandonment of the Grievance.**

Per Section 19.D.3: All notifications, requests, and decisions shall be **in writing**.

⚠️ **Contact your Union Representative (EXCO member) immediately when you identify a potential violation. Do not wait.**"""
    },

    "What Evidence to Save": {
        "icon": "📁",
        "content": """## What Evidence to Save

If you believe the contract has been violated, start saving evidence immediately. Do not wait.

**Always Save These:**
- ✅ Pay stubs (every month — compare to your actual schedule)
- ✅ Published bid lines (Initial and Final Line Awards)
- ✅ Trip pairings (before and after any changes)
- ✅ Crew Scheduling communications (calls, emails, texts)
- ✅ Schedule changes (screenshot before and after)
- ✅ Duty times (actual vs scheduled)
- ✅ Rest period records
- ✅ FIFO list positions (screenshot from Company intranet)

**For Pay Disputes:**
- ✅ Block time records
- ✅ Duty start and end times
- ✅ TAFD (Time Away From Domicile) calculations
- ✅ Open Time pickup confirmations
- ✅ Junior Assignment notifications

**For Scheduling Disputes:**
- ✅ Original published line
- ✅ Any reassignment notifications
- ✅ Day Off records (were minimums met?)
- ✅ Rest period calculations between assignments
- ✅ Training schedule vs line schedule conflicts

**For Reserve Disputes:**
- ✅ RAP start/end times
- ✅ Initial Call times and your response times
- ✅ FIFO list at time of assignment
- ✅ Whether proper FIFO order was followed

**For Grievances:**
- ✅ All emails between you, the Company, and your Union Rep related to the grievance
- ✅ Written grievance filing with date submitted
- ✅ Company's written response/decision
- ✅ Dates of each step (informal discussion, written filing, meeting, decision)
- ✅ Names of managers and representatives involved

**How to Save:**
- Screenshot everything on your phone immediately
- Forward emails to your personal email
- Keep a simple log: Date | What Happened | Contract Section
- Save files with dates in the filename (e.g., "2026-02-07_schedule_change.png")

⚠️ **The Company's records can change. Your personal records are your protection.**"""
    },
}

# ============================================================
# CONTRACT CHAPTERS — Clickable section buttons on empty state
# ============================================================
CONTRACT_CHAPTERS = [
    ("Section 3", "Compensation", "What is my hourly pay rate as a Captain?"),
    ("Section 5", "Retirement & Insurance", "What retirement benefits does the contract provide?"),
    ("Section 6", "Expenses & Lodging", "What is the per diem rate?"),
    ("Section 7", "Deadheading", "What are the deadhead pay rules?"),
    ("Section 8", "Leaves of Absence", "What types of leave am I entitled to?"),
    ("Section 10", "Sick Leave", "What are the rules for calling in sick?"),
    ("Section 11", "PTO", "How does PTO work?"),
    ("Section 12", "Training", "What are the training pay rules?"),
    ("Section 13", "Hours of Service", "What are the duty time limits?"),
    ("Section 14", "Scheduling", "How many days off am I guaranteed per month?"),
    ("Section 15", "Reserve", "What are the different reserve types?"),
    ("Section 17", "Furlough & Recall", "What are the furlough and recall rules?"),
]

# ============================================================
# ANSWER MODIFIERS — "What would change this answer?" (currently unused)
# ============================================================

ANSWER_MODIFIERS = {
    "Pay": """**Factors that could change this answer:**
- Your line type (Regular, Composite, Reserve, TDY, Domicile Flex) may trigger different pay rules
- Whether the duty was on a scheduled Day Off (175% premium may apply)
- Whether this was an Open Time pickup (1.5x premium) or Junior Assignment (JA Premium)
- Whether the trip involved international operations (different per diem)
- Whether a Letter of Agreement (LOA) or MOU modifies the standard pay provision
- Actual vs scheduled duty times may differ, changing Duty Rig calculations""",

    "Reserve": """**Factors that could change this answer:**
- Your reserve type (R-1, R-2, R-3, R-4) — each has different rules
- Whether you were at Domicile or out-of-Domicile when contacted
- Whether you were reassigned from one reserve type to another
- Whether the assignment conflicts with a scheduled Day Off
- Your position on the FIFO list
- Whether a Letter of Agreement (LOA) or MOU modifies the provision""",

    "Scheduling": """**Factors that could change this answer:**
- Your line type (Regular, Composite, Reserve, TDY, Domicile Flex)
- Whether circumstances were within or beyond the Company's control (IROP)
- Whether you are at Domicile or out-of-Domicile
- Whether the change is a Reassignment vs a voluntary trade/drop
- Whether Training conflicts with your schedule
- Whether a Letter of Agreement (LOA) or MOU modifies the provision""",

    "Training": """**Factors that could change this answer:**
- Training type: Initial, Upgrade, Transition, or Recurrent
- Duration: Short-Term vs Long-Term (15+ days)
- Location: at Domicile or away from Domicile
- Whether training falls on a scheduled Day Off
- Whether you are a Check Airman, Instructor, or line pilot""",

    "General": """**Factors that could change this answer:**
- Your line type and current duty status
- Whether a Letter of Agreement (LOA) or MOU modifies the provision
- Whether this involves domestic or international operations
- Whether circumstances are within or beyond the Company's control
- Your position (Captain vs First Officer) and seniority"""
}

# ============================================================
# FLEET — Aircraft types at this airline
# ============================================================
FLEET_TYPES = ['B737']
DEFAULT_AIRCRAFT = 'B737'

# Aircraft shorthand (airline-specific)
AIRCRAFT_SHORTHAND = [
    (r"\b73\b", "b737"),
    (r"\b737\b", "b737"),
    (r"\b76\b", "b767"),
    (r"\b767\b", "b767"),
]

# ============================================================
# SYSTEM PROMPT — Airline-specific key definitions
# Injected into the system prompt so the AI knows this contract's terms.
# ============================================================
SYSTEM_PROMPT_KEY_DEFINITIONS = """
KEY DEFINITIONS (from Section 2):
- Block Time = Brakes released to brakes set. Flight Time = Brake release to block in.
- Day = Calendar Day 00:00–23:59 LDT. Day Off = Scheduled Day free of ALL Duty at Domicile.
- DPG = 3.82 PCH minimum per Day of scheduled Duty.
- Duty Period = Continuous time from Report for Duty until Released and placed into Rest. Rest Period ≠ Day Off.
- Duty Rig = 1 PCH per 2 hours Duty, prorated minute-by-minute. Trip Rig = TAFD ÷ 4.9.
- Extension = Involuntary additional Flight/Duty after last segment of Trip Pairing.
- FIFO = First In, First Out reserve scheduling per Section 15.
- JA = Junior Assignment: involuntary Duty on Day Off, inverse seniority (most junior first).
- PCH = Pay Credit Hours — the unit of compensation.
- R-1 = In-Domicile Short Call (Duty). R-2 = Out-of-Domicile Short Call (Duty). R-3 = Long Call. R-4 = Airport RAP (Duty).
- Composite Line = Blank line constructed after SAP. Domicile Flex Line = Reserve with 13+ consecutive Days Off, all Workdays R-1.
- Ghost Bid = Line a Check Airman bids but cannot be awarded; sets new MPG.
- Phantom Award = Bidding higher-paying Position per seniority to receive that pay rate.
"""

# ============================================================
# SYSTEM PROMPT — Pay-specific rules (injected when pay question detected)
# ============================================================
PAY_PROMPT_TEMPLATE = """
CURRENT PAY RATES:
DOS = July 24, 2018. Per Section 3.B.3, rates increase 2% annually on DOS anniversary. As of today: {pay_increases} increases (July 2019–July {dos_year_latest}). CURRENT RATE = Appendix A DOS rate × {pay_multiplier:.5f}. Always use DOS column, multiply by {pay_multiplier:.5f}, show math. If longevity year is stated, look up that rate in Appendix A and calculate. Do NOT say you cannot find the rate if a year is provided.

PAY QUESTION RULES:
When pay/compensation is involved:
- Identify position and longevity year if provided
- Calculate ALL four pay provisions and compare:
  1. Block PCH: [flight time]
  2. Duty Rig: [total duty hours] ÷ 2 = [X] PCH (if exact times unknown, show "Minimum Duty Rig estimate" using available info — NEVER say "cannot calculate")
  3. DPG: 3.82 PCH
  4. Trip Rig: [TAFD hours] ÷ 4.9 = [X] PCH (or "Not applicable — single-day duty period")
  → Pilot receives the GREATER of these
- Show all math: PCH values AND dollar amounts
- Do NOT use dollar signs ($) — write "191.22/hour" not "$191.22/hour" (Streamlit renders $ as LaTeX)
- End with: "The pilot should be paid [X] PCH × [rate] = [total]"

DUTY RIG ESTIMATION: If exact times are missing, calculate minimum estimate from what IS known. For assigned trips: duty starts minimum 1 hour before departure. For reserve: duty starts at RAP DOT or 1 hour before departure (whichever earlier). Always provide estimate.

OVERTIME PREMIUM (Section 3.Q.1):
150% pay for duty on scheduled Day Off applies ONLY when caused by: (a) circumstances beyond Company control (weather, mechanical, ATC, customer accommodation), OR (b) assignment to remain with aircraft for repairs.
- If cause is NOT stated: quote trigger conditions, present 150% as CONDITIONAL, mark AMBIGUOUS
- Do NOT automatically apply 150% without a stated trigger
- OVERTIME SCOPE DISPUTE (REQUIRED ONLY when a single duty period begins on a workday and extends into a Day Off): "⚠️ OVERTIME SCOPE DISPUTE: Even if the 150% premium applies, the contract does not specify whether it covers all PCH earned in the duty period or only the PCH attributable to the Day Off hours. Both interpretations are reasonable, and this is a potential area of dispute."
  Do NOT include this dispute paragraph when duty is entirely on a Day Off (e.g., Junior Assignment, full Day Off duty). The scope dispute only exists when there is a split between workday hours and Day Off hours within the same duty period.

RESERVE PAY:
- R-1 and R-2 are DUTY — duty starts at scheduled RAP DOT, not when called or when flight departs
- Use FULL duty period for Duty Rig: from RAP DOT or 1hr before departure (whichever earlier) to release
- Per Section 3.F.1.b: Reserve Pilot receives GREATER of DPG or PCH from assigned trip
- If duty extends past RAP or into Day Off, you MUST address: extension analysis, 0200 LDT rule (15.A.7-8), overtime premium eligibility, and whether single duty period = one Workday (Section 3.D.2)
"""

# ============================================================
# GRIEVANCE PATTERN ALERT TEMPLATES
# Section numbers and dollar amounts are airline-specific.
# The detection logic (regex) lives in the main app.
# ============================================================
GRIEVANCE_ALERTS = {
    'duty_over_16': "⚠️ DUTY TIME ALERT: {hours} hours exceeds the 16-hour maximum for a basic 2-pilot crew (Section 13.F.1). Verify crew complement — 18hr max for augmented (3-pilot), 20hr max for heavy (4-pilot). If exceeded, per Section 14.N, the Company must remove the pilot from the trip and place into rest.",
    'duty_over_14': "⚠️ REST REQUIREMENT ALERT: {hours} hours of duty triggers the 12-hour minimum rest requirement (Section 13.G.1 — duty over 14 hours requires 12 hours rest, not the standard 10 hours).",
    'rest_under_10': "⚠️ REST VIOLATION ALERT: {hours} hours of rest is below the 10-hour minimum required after duty of 14 hours or less (Section 13.G.1). This is a potential grievance.",
    'rest_under_12': "⚠️ REST ALERT: {hours} hours rest — verify prior duty period length. If prior duty exceeded 14 hours, minimum rest is 12 hours, not 10 (Section 13.G.1).",
    'ja_checklist': "⚠️ JA CHECKLIST: Verify (1) inverse seniority order was followed (Section 14.O.1), (2) whether this is 1st or 2nd JA in rolling 3-month period for premium rate (Section 3.R), (3) one-extension-per-month limit if extended (Section 14.N.6).",
    'ja_day_off': "⚠️ DAY-OFF JA: Per Section 14.O, JA on a Day Off requires 200% premium (1st in 3mo) or 250% (2nd in 3mo). Verify the pilot was not senior to other available pilots.",
    'extension': "⚠️ EXTENSION CHECKLIST: Per Section 14.N — (1) only ONE involuntary extension per month is permitted, (2) extension cannot violate duty time limits (Section 13.F), (3) extension cannot cause a pilot to miss a scheduled Day Off beyond 0200 LDT (Section 15.A.7).",
    'day_off_work': "⚠️ DAY-OFF WORK: Determine if this was a Junior Assignment (200%/250% per Section 3.R) or voluntary Open Time pickup (150% per Section 3.P). Assignments may be scheduled up to 0200 LDT into a Day Off (Section 15.A.7) — duty past 0200 into a Day Off is a potential violation.",
    'min_days_off': "⚠️ DAYS OFF MINIMUM: Per Section 14.E.2.d (LOA #15), minimum is 13 Days Off for a 30-day month and 14 Days Off for a 31-day month. Verify the published line meets this requirement.",
    'positive_contact': "⚠️ POSITIVE CONTACT REQUIRED: Per MOU #2 (Page 381), schedule changes require Positive Contact via the pilot's authorized phone number. Email, text, or voicemail alone is NOT sufficient — the pilot must acknowledge the change verbally. Failure to make Positive Contact means the change is not effective.",
    'rest_interruption': "⚠️ REST INTERRUPTION: Per Section 13.H.7, if a pilot's rest is interrupted (e.g., hotel security, repeated phone calls), the required rest period begins anew. Only emergency/security notifications are exempt from this rule.",
    'reserve_reassignment': "⚠️ RESERVE REASSIGNMENT: Per MOU #4 (Page 383), Crew Scheduling cannot reassign a pilot performing a Trip Pairing to a Reserve Assignment. Reserve type changes require 12-hour notice (MOU #4 provision 8). If more than 2 pilots may be reassigned, inverse seniority applies (MOU #4 provision 13).",
}

# Duty time thresholds for grievance detection
DUTY_MAX_BASIC = 16     # 2-pilot crew
DUTY_MAX_AUGMENTED = 18  # 3-pilot crew
DUTY_MAX_HEAVY = 20      # 4-pilot crew
REST_MIN_STANDARD = 10   # After duty ≤ 14 hours
REST_MIN_EXTENDED = 12   # After duty > 14 hours
REST_TRIGGER_THRESHOLD = 14  # Duty hours that trigger extended rest

# ============================================================
# PAY CALCULATION — Premium multipliers (Section 3)
# ============================================================
PAY_PREMIUMS = {
    'open_time': 1.5,           # Section 3.P.2
    'overtime': 1.5,            # Section 3.Q
    'ja_first': 2.0,            # Section 3.R.1
    'ja_second': 2.5,           # Section 3.R.2
    'check_airman': 1.15,       # Section 3.S.1
    'apd': 1.20,                # Section 3.S.2
    'check_airman_day_off': 1.75,  # Section 3.S.5.b
}

# DPG value (PCH)
DPG_VALUE = 3.82

# Per diem answer template — section references are airline-specific
PER_DIEM_ANSWER_TEMPLATE = """📄 CONTRACT LANGUAGE: "For Duty or other Company-Directed Assignments that are performed within the Contiguous United States, including all time during a layover in the United States, Fifty-Six Dollars ($56) per Day."
📍 Section 6.C.2.a, Page 99

"For Duty or other Company-directed Assignment that contains a segment that is to or from an airport outside the contiguous United States, including all layover time in a location outside of the contiguous United States: Seventy-Two Dollars ($72) per Day."
📍 Section 6.C.2.b, Page 100

"The Per Diem rates, as provided in subparagraph 6.C., shall be increased by one (1) Dollar ($1.00) per Day on each anniversary date of the Agreement."
📍 Section 6.C.2.c, Page 100

📝 EXPLANATION: Per the contract, pilots receive Per Diem for duty assignments that include rest periods away from their domicile. The base rates (DOS July 24, 2018) were {base_domestic}/day domestic and {base_international}/day international. Per Section 6.C.2.c, rates increase by {annual_increase}/day on each contract anniversary.

As of today, there have been {anniversaries} anniversary increases (July 2019 through July {latest_year}):
- Domestic (contiguous U.S.): {base_domestic} + {anniversaries} = **{current_domestic}/day**
- International: {base_international} + {anniversaries} = **{current_international}/day**

Per Diem is calculated from the time of scheduled or actual report time at Domicile (whichever is later) until the scheduled or actual conclusion of duty at Domicile (whichever is later). Per Diem is only paid for assignments that include a rest period away from Domicile (Section 6.C.1).

🔵 STATUS: CLEAR - The contract explicitly states per diem rates in Section 6.C.2 and the annual increase formula in Section 6.C.2.c.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""


