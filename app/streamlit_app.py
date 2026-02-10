import streamlit as st
import pickle
import numpy as np
from openai import OpenAI
from anthropic import Anthropic
import time
import sys
import threading
import json
import os
from pathlib import Path
from datetime import datetime

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

from contract_manager import ContractManager
from contract_logger import ContractLogger

# Page config
st.set_page_config(
    page_title="AskTheContract",
    page_icon="✈️",
    layout="wide"
)

# ============================================================
# FEATURE 1: QUICK REFERENCE CARDS
# Static content, zero API calls, loads instantly
# ============================================================

QUICK_REFERENCE_CARDS = {
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

**How to Save:**
- Screenshot everything on your phone immediately
- Forward emails to your personal email
- Keep a simple log: Date | What Happened | Contract Section
- Save files with dates in the filename (e.g., "2026-02-07_schedule_change.png")

⚠️ **The Company's records can change. Your personal records are your protection.**"""
    }
}

# ============================================================
# FEATURE 2: CANONICAL QUESTION LABELS
# Keyword matching only, no AI, no embeddings
# ============================================================

QUESTION_CATEGORIES = {
    "Pay → Hourly Rate": ['hourly rate', 'pay rate', 'what do i make', 'how much do i make', 'rate of pay', 'longevity rate', 'current rate'],
    "Pay → Daily Pay Guarantee": ['dpg', 'daily pay guarantee', 'minimum pay per day', 'daily guarantee'],
    "Pay → Duty Rig": ['duty rig', 'duty day pay', '1:2'],
    "Pay → Trip Rig / TAFD": ['trip rig', 'tafd', 'time away from domicile'],
    "Pay → Overtime / Premium": ['overtime', 'open time premium', 'premium pay', 'time and a half'],
    "Pay → Junior Assignment Premium": ['junior assignment premium', 'ja premium', 'ja pay'],
    "Pay → General Calculation": ['pay', 'paid', 'compensation', 'wage', 'salary', 'earning', 'pch'],
    "Reserve → Types & Definitions": ['reserve type', 'r-1', 'r-2', 'r-3', 'r-4', 'what is reserve'],
    "Reserve → FIFO": ['fifo', 'first in first out', 'reserve order'],
    "Reserve → Availability / RAP": ['reserve availability', 'rap', 'on call', 'call out'],
    "Reserve → Day-Off Reassignment": ['reserve day off', 'called on day off', 'junior assigned', 'involuntary assign'],
    "Scheduling → Days Off": ['day off', 'days off', 'time off', 'week off', 'off per week', 'off a week', 'days a week'],
    "Scheduling → Rest Periods": ['rest period', 'rest requirement', 'minimum rest', 'duty free'],
    "Scheduling → Line Construction": ['line construction', 'bid line', 'regular line', 'composite line', 'reserve line', 'domicile flex'],
    "Scheduling → Reassignment": ['reassign', 'reassignment', 'schedule change'],
    "Scheduling → Duty Limits": ['duty limit', 'duty time', 'max duty', 'maximum duty'],
    "Training": ['training', 'upgrade', 'transition', 'simulator', 'check ride', 'recurrent'],
    "Seniority": ['seniority', 'seniority list', 'seniority number', 'bid order'],
    "Grievance": ['grievance', 'grieve', 'dispute', 'arbitration', 'system board'],
    "TDY": ['tdy', 'temporary duty', 'tdy line'],
    "Vacation / Leave": ['vacation', 'leave', 'sick leave', 'bereavement', 'military leave', 'fmla'],
    "Benefits": ['insurance', 'health', 'medical', 'dental', 'retirement', '401k'],
    "Furlough": ['furlough', 'recall', 'laid off', 'reduction'],
}

def classify_question(question_text):
    """Classify by keyword matching. No AI, no embeddings."""
    q_lower = question_text.lower()
    best_match = None
    best_count = 0
    for category, keywords in QUESTION_CATEGORIES.items():
        count = sum(1 for kw in keywords if kw in q_lower)
        if count > best_count:
            best_count = count
            best_match = category
    return best_match if best_match else "General Contract Question"

# ============================================================
# FEATURE 3: "WHAT WOULD CHANGE THIS ANSWER?"
# Static pre-written text per category
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

def get_answer_modifier(category_label):
    """Return static modifier text. No AI."""
    if not category_label:
        return ANSWER_MODIFIERS["General"]
    for key in ANSWER_MODIFIERS:
        if key.lower() in category_label.lower():
            return ANSWER_MODIFIERS[key]
    return ANSWER_MODIFIERS["General"]

# ============================================================
# FEATURE 4: ANSWER RATING
# Logging only, no AI processing
# ============================================================

def log_rating(question_text, rating, comment=""):
    """Log a rating to file. No AI."""
    try:
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        rating_file = log_dir / "answer_ratings.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question_text,
            "rating": rating,
            "comment": comment
        }
        with open(rating_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return True
    except:
        return False

# ============================================================
# SEMANTIC SIMILARITY CACHE
# ============================================================
class SemanticCache:
    SIMILARITY_THRESHOLD = 0.96
    MAX_ENTRIES = 500

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = {}

    def lookup(self, embedding, contract_id):
        with self._lock:
            entries = self._entries.get(contract_id, [])
            for cached_emb, cached_q, cached_answer, cached_status, cached_time in entries:
                score = np.dot(embedding, cached_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(cached_emb)
                )
                if score > self.SIMILARITY_THRESHOLD:
                    return cached_answer, cached_status, cached_time
        return None

    def store(self, embedding, question, answer, status, response_time, contract_id):
        with self._lock:
            if contract_id not in self._entries:
                self._entries[contract_id] = []
            entries = self._entries[contract_id]
            if len(entries) >= self.MAX_ENTRIES:
                entries.pop(0)
            entries.append((embedding, question, answer, status, response_time))

    def clear(self, contract_id=None):
        with self._lock:
            if contract_id:
                self._entries.pop(contract_id, None)
            else:
                self._entries = {}

@st.cache_resource
def get_semantic_cache():
    return SemanticCache()

# ============================================================
# INIT FUNCTIONS
# ============================================================

@st.cache_resource
def load_api_keys():
    import os
    keys = {}
    
    # Try environment variables first (Railway)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    if anthropic_key and openai_key:
        keys['anthropic'] = anthropic_key
        keys['openai'] = openai_key
        return keys
    
    # Then try Streamlit secrets
    try:
        keys['openai'] = st.secrets["OPENAI_API_KEY"]
        keys['anthropic'] = st.secrets["ANTHROPIC_API_KEY"]
        return keys
    except:
        pass
    
    # Then try file
    try:
        with open('api_key.txt', 'r') as f:
            for line in f:
                if 'OPENAI_API_KEY' in line:
                    keys['openai'] = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                if 'ANTHROPIC_API_KEY' in line:
                    keys['anthropic'] = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
        return keys
    except FileNotFoundError:
        st.error("API keys not found. Set ANTHROPIC_API_KEY and OPENAI_API_KEY environment variables.")
        st.stop()
@st.cache_resource
def init_clients():
    keys = load_api_keys()
    openai_client = OpenAI(api_key=keys['openai'])
    anthropic_client = Anthropic(api_key=keys['anthropic'])
    return openai_client, anthropic_client

@st.cache_resource
def init_contract_manager():
    return ContractManager()

@st.cache_resource
def init_logger():
    return ContractLogger()

@st.cache_resource
def load_contract(contract_id):
    manager = init_contract_manager()
    chunks, embeddings = manager.load_contract_data(contract_id)
    return chunks, embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@st.cache_data(ttl=86400, show_spinner=False)
def get_embedding_cached(question_text, _openai_client):
    response = _openai_client.embeddings.create(
        input=question_text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# ============================================================
# FORCE-INCLUDE CHUNKS
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
                        break
    return forced

def search_contract(question, chunks, embeddings, openai_client, max_chunks=75):
    question_embedding = get_embedding_cached(question, openai_client)
    question_lower = question.lower()
    forced_chunks = find_force_include_chunks(question_lower, chunks)

    similarities = []
    for i, chunk_embedding in enumerate(embeddings):
        score = cosine_similarity(question_embedding, chunk_embedding)
        similarities.append((score, chunks[i]))

    similarities.sort(reverse=True, key=lambda x: x[0])
    embedding_chunks = [chunk for score, chunk in similarities[:max_chunks]]

    seen_ids = set()
    merged = []
    for chunk in forced_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
    for chunk in embedding_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_chunks:
                break
    return merged

# ============================================================
# API CALL
# ============================================================
def _ask_question_api(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history=None):
    start_time = time.time()

    pay_keywords = ['pay', 'rate', 'hourly', 'salary', 'wage', 'compensation', 'earning', 'make per hour', 'dpg', 'scale', 'duty rig', 'trip rig', 'pch', 'overtime', '150%', '200%', '175%', 'premium']
    scheduling_keywords = ['day off', 'days off', 'rest period', 'rest requirement', 'schedule', 'line construction', 'composite line', 'regular line', 'reserve line', 'bid line', 'workday', 'work day', 'consecutive days', 'week off', 'time off', 'duty free', 'days a week', 'off per week', 'off a week', 'reserve', 'r-1', 'r-2', 'r-3', 'r-4', 'r1', 'r2', 'r3', 'r4', 'rap', 'fifo', 'junior assignment', 'extension', 'reassign']

    question_lower = question.lower()
    is_pay_question = any(keyword in question_lower for keyword in pay_keywords)
    is_scheduling_question = any(keyword in question_lower for keyword in scheduling_keywords)

    if is_pay_question or is_scheduling_question:
        max_chunks = 100
    else:
        max_chunks = 75

    relevant_chunks = search_contract(question, chunks, embeddings, openai_client, max_chunks=max_chunks)

    context_parts = []
    for chunk in relevant_chunks:
        section_info = chunk.get('section', 'Unknown Section')
        aircraft_info = f", Aircraft: {chunk['aircraft_type']}" if chunk.get('aircraft_type') else ""
        context_parts.append(f"[Page {chunk['page']}, {section_info}{aircraft_info}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA). Your role is to provide accurate, unbiased contract analysis based solely on the contract language provided to you.

SCOPE LIMITATION:
This tool ONLY searches the {airline_name} pilot union contract (JCBA). It does NOT have access to:
- FAA regulations or Federal Aviation Regulations (FARs)
- Company Operations Manuals or Standard Operating Procedures (SOPs)
- Company policies, memos, or bulletins
- Other labor agreements or side letters not included in the JCBA
- State or federal employment laws
If a question appears to be about any of these sources, clearly state: "This tool only searches the {airline_name} pilot contract (JCBA) and cannot answer questions about FAA regulations, company manuals, or other policies outside the contract."

CONVERSATION CONTEXT:
The user may ask follow-up questions that reference previous answers. When this happens, use the conversation history to understand what they are referring to. Maintain the same position (Captain or First Officer), aircraft type, and other parameters from the previous question unless the user explicitly changes them. For example, if the previous answer was about a B737 Captain and the user asks "what about year 12?" - recalculate using the Year 12 Captain rate for the same aircraft. Always provide a complete answer with full contract citations even for follow-up questions.

CORE PRINCIPLES:
1. Quote exact contract language - always use the precise wording from the contract
2. Cite every quote with section number and page number
3. Never interpret beyond what the contract explicitly states
4. Never assume provisions exist that are not in the provided text
5. Never use directive language like "you get" or "company owes" - instead say "the contract states" or "per the contract language"
6. Always acknowledge when the contract is silent on a topic
7. When multiple provisions may apply, cite all of them

ANALYSIS RULES:
- Read ALL provided contract sections before forming your answer
- Look for provisions that may apply from different sections (pay, scheduling, reserve, hours of service, etc.)
- Check for defined terms - many words have specific contract definitions
- Pay attention to qualifiers like "shall", "may", "except", "unless", "notwithstanding", "provided"
- Note the difference between "scheduled" vs "actual" and "assigned" vs "awarded"
- Distinguish between different pilot categories: Regular Line holders, Reserve pilots (R-1, R-2, R-3, R-4), Composite Line holders, TDY pilots, Domicile Flex Line holders
- Distinguish between different types of assignments: Trip Pairings, Reserve Assignments, Company-Directed Assignments, Training, Deadhead
- When a provision applies only to specific categories, state which categories clearly

SECTION 2 – KEY CONTRACT DEFINITIONS (Condensed Reference):
These are official contract definitions from Section 2. Always use these meanings when interpreting contract language:
- Active Service = Available for Assignment, on Sick Leave, Vacation, or LOA where Longevity accrues. Furlough/unpaid LOA ≠ Active Service.
- Agreement = This CBA + all Side Letters, MOUs, and LOAs.
- Aircraft Type = Specific make/model per FARs (e.g., B737, B767).
- Assignment = Flight, Reserve, Training, or any Company-directed activity; also an awarded Vacancy.
- Block Time = Brakes released (pushback/taxi) to brakes set at destination.
- Captain = Pilot in Command, holds Captain bid status.
- Check Airman (Full) = Company/FAA-approved to instruct, train, check in aircraft, simulator, or classroom.
- Check Airman (Line/LCA) = Approved for instruction/checking during line operations or classroom.
- Composite Line = Blank line in Bid Package; constructed after SAP with any mix of Duty/Days Off.
- Company-Directed Assignment = Scheduled work at Company direction; a scheduled Assignment on a Pilot's Line.
- Company Provided Benefits = Health Insurance, AD&D, Life Insurance, 401(k). Some at no cost; others cost-shared or Pilot-paid (e.g., STD/LTD buy-up).
- Daily Pay Guarantee (DPG) = 3.82 PCH minimum per Day of scheduled Duty.
- Day = Calendar Day 00:00–23:59 LDT.
- Day Off = Scheduled Day free of ALL Duty, taken at Pilot's Domicile.
- Deadhead Travel = Movement by air/surface to/from a Flight or Company-Directed Assignment.
- Domicile = Company-designated Airport where Pilots are based (regardless of actual Residence).
- Domicile Flex Line = Reserve Line with single block of 13+ consecutive Days Off; all Workdays are R-1 RAPs.
- Duty = Any Company-directed activity: Flight, Deadhead, Training, R-1/R-2/R-4 Reserve, admin work, positioning.
- Duty Assignment = Any requirement to be on Duty or Available (except R-3) counted toward Flight/Duty Time limits.
- Duty Period = Continuous time from Report for Duty until Released from Duty and placed into Rest.
- Duty Rig = Pay credit ratio 1:2 — one PCH per two hours of Duty, prorated minute-by-minute.
- Eligible Dependent(s) = Spouse, children, domestic partner, or others qualifying for benefits/tax purposes per Agreement or law.
- Eligible Pilot = A Pilot who possesses the qualifications to be awarded or Assigned to a Position or Assignment.
- Extension = Involuntary Assignment to additional Flight/Duty after last segment of originally scheduled Trip Pairing, within legality and Section 14 limits.
- FIFO = First In, First Out reserve scheduling per Section 15 for assigning Trips to Reserve Pilots.
- Final Line/Final Bid Awards = Pilot's final awarded Line after Composite Line construction.
- First Officer = Second-in-Command; assists/relieves Captain.
- Flight Time = Brake release to block in (hours/minutes).
- Furlough = Voluntary/involuntary removal from Active Service due to reduction in force.
- Ghost Bid = Line a Full-Time Check Airman/Instructor bids for but cannot be awarded; establishes new MPG for the Month.
- Grievance = Dispute for alleged Company violation(s) of this Agreement.
- Initial Line Award = Pilot's Line award prior to Integration Period.
- Junior Assignment (JA) = Involuntary Assignment to Duty on Day Off, inverse Seniority Order (most junior first).
- Known Flying = All flight segments known before Monthly Initial Line Bid Period begins.
- LOA = Letter of Agreement — addendum separate from main CBA body.
- Monthly Bid Period = The bidding cycle each Month per Section 14.
- Monthly Pay Guarantee (MPG) = Minimum PCH value for all published Initial/Final Lines.
- MOU = Memorandum of Understanding.
- Open Time = Trip Pairings/Reserve Assignments not built into Lines or that become available during the Month.
- PCH = Pay Credit Hours — the unit of compensation.
- Phantom Award/Phantom Bid = Bidding for Vacancy in higher-paying Position (per seniority) to receive that higher pay rate.
- Position = Captain or First Officer on a specific Aircraft Type at a Domicile.
- RAP = Reserve Availability Period (R-1 or R-2 assignment).
- Regular Line = Planned sequence of Trip Pairings (may include limited R-1 RAPs, max 6).
- Reserve = Assignment (R-1/R-2/R-3/R-4) where Pilot is available for Company Assignment.
- R-1 = In-Domicile Short Call Reserve (Duty). R-2 = Out-of-Domicile Short Call Reserve (Duty). R-3 = Long Call Reserve. R-4 = Airport RAP (Duty).
- Rest Period = Minimum consecutive hours free from Duty between assignments — NOT a Day Off.
- SAP = Schedule Adjustment Period — process to modify Initial Line Award via Pick-Up and Trade.
- Seniority = Position on System Seniority List based on length of service from Date of Hire.
- Split-Trip Pairing = Trip Pairing containing both Flight Segments and a RAP Assignment.
- TDY = Temporary Duty Vacancy at location other than Pilot's Domicile.
- Trip Pairing = One or more Duty Periods with any mix of Flight/Deadhead Segments, beginning and ending at Domicile.
- Trip Rig = Pay credit based on elapsed trip time (as opposed to Duty Rig).
- Vacancy = An open Position (Domicile/Aircraft Type/Status) to be filled per Section 18.

CURRENT PAY RATE GUIDANCE:
The contract Date of Signing (DOS) is July 24, 2018. Per Section 3.B.3, Hourly Pay Rates increase by 2% annually on each anniversary of the DOS. As of February 2026, there have been 7 annual increases (July 2019 through July 2025). Therefore: CURRENT RATE = DOS rate from Appendix A × 1.02^7 (which equals × 1.14869). Always use the DOS column from Appendix A, multiply by 1.14869, and show your math. Example: Year 12 B737 Captain DOS rate $189.19 × 1.14869 = $217.33/hour.
MANDATORY: If the Appendix A DOS rate appears in the provided contract sections, you MUST calculate and display the final dollar amount. If the pilot's longevity year is stated (e.g., "12 year captain"), look for that rate in Appendix A, apply the 1.14869 multiplier, and show the final pay in dollars. Do NOT say you cannot find the rate if a longevity year is provided — use the Appendix A data in the provided sections. If the specific rate truly does not appear in any provided section, use the example rate ($189.19 for Year 12 B737 Captain) and note it as an example.

PAY QUESTION RULES:
When the question involves pay or compensation, you MUST:
- Identify the pilot's position (Captain or First Officer) and longevity year if provided
- Calculate all potentially applicable pay provisions including:
  * Daily Pay Guarantee (DPG): 3.82 PCH multiplied by hourly rate
  * Duty Rig: total duty hours divided by 2, multiplied by hourly rate
    DUTY RIG ESTIMATION RULE: If exact RAP start time or release time is not stated, you MUST still calculate a minimum Duty Rig estimate using what IS known. For assigned trips: duty begins at MINIMUM 1 hour before scheduled departure. For reserve pilots: duty begins at the RAP DOT if stated, or 1 hour before departure if RAP time is not given. Release time is after landing (use landing time as minimum). Show this as "Minimum Duty Rig estimate" and note what information would be needed for an exact calculation. NEVER say "cannot calculate" — always provide the minimum estimate.
  * Trip Rig (TAFD): total TAFD hours divided by 4.9, multiplied by hourly rate
  * Scheduled PCH if provided in the scenario
  * Overtime Premium: PCH multiplied by hourly rate multiplied by 1.5 — BUT ONLY when trigger conditions are met (see OVERTIME PREMIUM RULES below)
- Show all math step by step — PCH values AND dollar amounts for EVERY calculation
- Quote the contract language that defines each calculation
- State which calculation the contract says applies, or if the contract does not specify
- ALWAYS end pay analysis with a clear summary: "The pilot should be paid [X] PCH × $[rate] = $[total]"

MANDATORY PAY COMPARISON TABLE:
Every pay answer MUST include a numbered comparison of ALL four calculations. Do NOT skip any. Use this exact format:
  1. Block PCH: [X] PCH
  2. Duty Rig: [total duty hours] ÷ 2 = [X] PCH (or "Minimum Duty Rig estimate: [X] PCH" if exact times are missing)
  3. DPG: 3.82 PCH
  4. Trip Rig: [TAFD hours] ÷ 4.9 = [X] PCH (or "Not applicable — single-day duty period" if no overnight TAFD)
  → The pilot receives the GREATER of these: [X] PCH ([name of winning calculation])
If you skip Duty Rig or any other calculation, your answer is INCOMPLETE. Always show all four.

OVERTIME PREMIUM RULES:
Section 3.Q.1 provides 150% pay for duty on a scheduled Day Off, but ONLY under specific trigger conditions:
  a. Circumstances beyond the Company's control (weather, mechanical, ATC, or customer accommodation); OR
  b. An Assignment to remain with an aircraft that requires time-consuming repairs.
CRITICAL: If the scenario does NOT state the cause of the Day Off duty, you MUST:
  - Quote the Section 3.Q.1 trigger conditions verbatim
  - State: "The overtime premium depends on WHY the pilot worked into his Day Off. If caused by circumstances beyond the Company's control (weather, mechanical, ATC, customer accommodation) or assignment to remain with an aircraft for repairs, 150% applies. If the trip was simply scheduled to end after midnight, the trigger conditions may not be met."
  - Do NOT automatically apply 150% — present it as conditional on the cause
  - This ambiguity about whether 150% applies MUST result in AMBIGUOUS status unless the scenario explicitly states the cause

OVERTIME SCOPE RULE:
Section 3.Q.1 states 150% applies to "the PCH earned when he is on Duty on a scheduled Day Off." When a single duty period spans both a workday and a Day Off, there are two reasonable interpretations:
  a. 150% applies to ALL PCH for the entire duty period (because the pilot WAS on duty on a Day Off)
  b. 150% applies only to the PCH attributable to the Day Off hours (because only that portion was "on Duty on a scheduled Day Off")
You MUST acknowledge both interpretations and flag this as a point of ambiguity. Do NOT silently pick one interpretation.
MANDATORY: Any time overtime premium is discussed AND the duty period spans both a workday and a Day Off, you MUST include this exact paragraph in your EXPLANATION section:
"⚠️ OVERTIME SCOPE DISPUTE: Even if the 150% premium applies, the contract does not specify whether it covers all PCH earned in the duty period or only the PCH attributable to the Day Off hours. Both interpretations are reasonable, and this is a potential area of dispute."
Do NOT omit this paragraph. It is REQUIRED whenever overtime and Day Off overlap occur together.

CRITICAL RESERVE PAY RULES:
When calculating pay for a Reserve Pilot who is assigned a trip:
- R-1 is DUTY (15.B.2.a). Duty time starts at the scheduled RAP DOT (Duty On Time), NOT when the flight departs or when the pilot was called. If an R-1 pilot has a RAP from noon to midnight and gets called at 3pm for a 6pm flight, his duty started at NOON.
- R-2 is DUTY (15.B.3.b). Same principle — duty starts at RAP DOT.
- For ANY scheduled trip, Duty begins 1 hour before the scheduled departure time. For reserve pilots, use whichever is EARLIER: the RAP DOT or 1 hour before flight departure.
- For Duty Rig calculations, use the FULL duty period: from RAP DOT or 1 hour before departure (whichever is earlier) to actual release from duty (when the pilot is back and released, not when the flight lands).
- If a reserve pilot works past the end of his scheduled RAP OR if a reserve pilot's duty (whether scheduled or actual) crosses into a scheduled Day Off, you MUST flag this and address ALL of the following:
  * EXTENSION / DAY OFF DUTY: You MUST include the "⏰ EXTENSION / DAY OFF DUTY ANALYSIS:" subsection in your EXPLANATION (see RESPONSE FORMAT below). This applies whether the duty past the RAP or into the Day Off was scheduled in advance or resulted from delays.
  * DAY OFF IMPACT: Check whether the next day is a scheduled Day Off. If so, cite the 0200 LDT rule (15.A.7-8) — assignments may be scheduled up to 0200 LDT into a Day Off. If the pilot works past 0200, this is a potential contract violation.
  * OVERTIME PREMIUM: Apply the OVERTIME PREMIUM RULES above. Do NOT automatically award 150%. Check whether the scenario states a qualifying trigger condition (Section 3.Q.1). If the cause is not stated, present the premium as conditional and flag ambiguity.
  * SECOND WORKDAY: Explicitly determine whether the work past midnight triggers a second Duty Period or Workday, which could mean additional DPG or other pay. You MUST address this directly — cite the overlapping-days provision (Section 3.D.2: a single Duty Period overlapping two Days constitutes one Workday) if applicable, and explicitly state your conclusion (e.g., "This is one continuous duty period, so it constitutes one Workday under Section 3.D.2"). Do NOT skip this step.
  * Do NOT skip this analysis. Any time actual duty extends beyond the scheduled RAP end time, these provisions MUST be discussed.
- Per Section 3.F.1.b, a Reserve Pilot receives the GREATER of: DPG, or the PCH earned from the assigned Trip Pairing (calculated per Section 3.E using block time, Duty Rig, or Trip Rig — whichever is greatest).
- Always compare ALL applicable calculations (block PCH, Duty Rig, Trip Rig, DPG) and pay the GREATEST value.

SCHEDULING AND REST QUESTION RULES:
When the question involves days off, rest periods, scheduling, or duty limits:
- Check provisions across Section 13 (Hours of Service), Section 14 (Scheduling), and Section 15 (Reserve Duty)
- Note that different line types (Regular, Composite, Reserve, TDY, Domicile Flex) have different rules
- Cite the specific line type or duty status each provision applies to
- Note minimum days off requirements for monthly line construction
- Note rest period requirements between duty assignments
- Distinguish between "Day Off" (defined term) and "Rest Period" (defined term)

STATUS DETERMINATION:
After your analysis, assign one of these statuses:

CLEAR - Use when:
- The contract explicitly and unambiguously answers the question
- All terms in the relevant provisions are defined
- There are no conflicting provisions
- The contract specifies exactly which calculation or rule applies

AMBIGUOUS - Use when:
- The contract uses undefined terms in the relevant provisions
- Multiple provisions could apply and the contract does not specify which one
- Provisions appear to conflict with each other
- The contract language is open to more than one reasonable interpretation
- The contract addresses the topic partially but not completely
- The scenario is missing key details needed to determine which provision applies (e.g., the cause of Day Off work is not stated, so the 150% trigger cannot be confirmed; the pilot's line type is not stated, so different rules could apply)
- A premium or benefit has trigger conditions and the scenario does not confirm whether those conditions are met

NOT ADDRESSED - Use when:
- The contract does not contain any language relevant to the question
- The provided sections do not cover the topic asked about

RESPONSE FORMAT:
Always structure your response exactly as follows:

📄 CONTRACT LANGUAGE: [Quote exact contract text with quotation marks]
📍 [Section number, Page number]

(Repeat for each relevant provision found)

📝 EXPLANATION: [Plain English explanation of what the contract language means, how provisions interact, and what the answer to the question is based solely on the contract text]

MANDATORY SUBSECTIONS WITHIN EXPLANATION (include when applicable):

⏰ EXTENSION / DAY OFF DUTY ANALYSIS: REQUIRED any time:
  - A pilot's actual duty extends beyond the end of a scheduled RAP or duty period, OR
  - A pilot's duty (whether scheduled or actual) crosses into a scheduled Day Off for ANY reason — including trips that were originally scheduled to end after midnight
You MUST include this header and:
(1) If duty extended beyond a scheduled RAP: State: "The pilot's scheduled RAP ended at [time] but the pilot was not released until [time]. This constitutes an extension of [X hour(s)] beyond the scheduled RAP."
(2) If duty crosses into a Day Off (whether scheduled or due to extension): State: "The pilot's duty continued until [time] into his scheduled Day Off. Per Section 15.A.7, assignments may be scheduled up to 0200 LDT into a Day Off. [State whether the duty ended before or after 0200 LDT.]"
(3) Quote the specific Section 14.N extension provisions from the provided contract sections in quotation marks with section/page citation. If 14.N language is not in the provided sections, state: "Section 14.N extension provisions should be reviewed but were not available in the retrieved contract sections."
(4) If applicable, state whether the extension is the pilot's first that month (relevant to the one-extension-per-month limit). If this information is not provided in the scenario, note that it is unknown.

⚠️ OVERTIME SCOPE DISPUTE: REQUIRED any time overtime premium is discussed AND the duty period spans both a workday and a Day Off. See OVERTIME SCOPE RULE above for required language.

🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence justification for the status]

⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.

IMPORTANT REMINDERS:
- If you cannot find relevant language in the provided sections, say so clearly
- Do not speculate about what the contract "probably" means or what "common practice" is
- Do not reference external laws, FARs, or regulations unless the contract itself references them
- Every claim you make must be traceable to a specific quoted provision
- When provisions from multiple sections are relevant, cite all of them
- Be thorough but concise - pilots need clear, actionable information"""

    messages = []

    # Add last 3 Q&A pairs as conversation context (questions and answers only, no chunks)
    if conversation_history:
        recent = conversation_history[-3:]
        for qa in recent:
            messages.append({
                "role": "user",
                "content": f"PREVIOUS QUESTION: {qa['question']}"
            })
            messages.append({
                "role": "assistant",
                "content": qa['answer']
            })

    user_content = f"""CONTRACT SECTIONS:
{context}

QUESTION: {question}

Answer:"""

    messages.append({"role": "user", "content": user_content})

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=messages
    )

    answer = message.content[0].text
    response_time = time.time() - start_time

    if '🔵 STATUS: CLEAR' in answer:
        status = 'CLEAR'
    elif '🔵 STATUS: AMBIGUOUS' in answer:
        status = 'AMBIGUOUS'
    else:
        status = 'NOT_ADDRESSED'

    return answer, status, response_time

# ============================================================
# TIER 1 — INSTANT ANSWERS (FREE, NO API CALL)
# ============================================================

# DOS rates from Appendix A (July 24, 2018)
PAY_RATES_DOS = {
    'B737': {
        'Captain': {1: 133.08, 2: 137.40, 3: 141.87, 4: 146.48, 5: 151.24, 6: 156.16, 7: 161.23, 8: 166.47, 9: 171.88, 10: 177.47, 11: 183.23, 12: 189.19},
        'First Officer': {1: 83.73, 2: 88.25, 3: 92.97, 4: 97.91, 5: 103.07, 6: 108.46, 7: 114.09, 8: 119.98, 9: 123.87, 10: 127.90, 11: 132.06, 12: 136.34},
    }
}

# 2% annual increase: DOS July 24, 2018. As of Feb 2026 = 7 increases (Jul 2019–Jul 2025)
PAY_MULTIPLIER = 1.02 ** 7  # 1.14868567
PAY_INCREASES = 7

# Contract definitions for instant lookup
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

import re

def _parse_pay_question(question_lower):
    """Parse a pay rate question and return (aircraft, position, year) or None."""
    # Extract year
    year_match = re.search(r'year\s*(\d{1,2})', question_lower)
    if not year_match:
        # Try "12 year" or "12-year"
        year_match = re.search(r'(\d{1,2})[\s-]*year', question_lower)
    if not year_match:
        return None
    year = int(year_match.group(1))
    if year < 1 or year > 12:
        return None

    # Extract position
    if 'captain' in question_lower or 'capt' in question_lower:
        position = 'Captain'
    elif 'first officer' in question_lower or 'fo ' in question_lower or 'f/o' in question_lower:
        position = 'First Officer'
    else:
        position = None

    # Extract aircraft — NAC only flies B737
    aircraft = 'B737'

    return aircraft, position, year

def _format_pay_answer(aircraft, position, year):
    """Build a formatted pay rate answer matching the app's output style."""
    # Determine which positions to show
    if position:
        combos = [(aircraft, position)]
    else:
        combos = [(aircraft, 'Captain'), (aircraft, 'First Officer')]

    rate_lines = []
    citation_parts = []

    for ac, pos in combos:
        dos_rate = PAY_RATES_DOS[ac][pos][year]
        current_rate = round(dos_rate * PAY_MULTIPLIER, 2)
        citation_parts.append(f'{pos} Year {year}: DOS rate {dos_rate:.2f}')
        rate_lines.append(f'- {pos} Year {year}: DOS rate {dos_rate:.2f} x 1.02^{PAY_INCREASES} (1.14869) = {current_rate:.2f} per hour')

    citation_text = '; '.join(citation_parts)

    answer = f"""📄 CONTRACT LANGUAGE: "B737 {citation_text}" 📍 Appendix A, Page 66

"On the Amendable Date of this Agreement and every anniversary thereafter until the Effective Date of an amended Agreement, Hourly Pay Rates shall increase by two percent (2%)." 📍 Section 3.B.3, Page 50

📝 EXPLANATION: The contract provides B737 Year {year} pay rates in Appendix A. The Date of Signing (DOS) is July 24, 2018. Per Section 3.B.3, pay rates increase by 2% annually on each anniversary. As of February 2026, there have been {PAY_INCREASES} annual increases (July 2019 through July 2025), so the current rates are:

{chr(10).join(rate_lines)}

🔵 STATUS: CLEAR - The contract explicitly provides the DOS pay rates in Appendix A and the annual increase formula in Section 3.B.3.

⚡ Instant answer from pre-computed pay table (no API cost)

⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

    return answer

def _format_definition_answer(term, definition):
    """Build a formatted definition answer matching the app's output style."""
    display_term = term.upper() if len(term) <= 4 else term.title()

    answer = f"""📄 CONTRACT LANGUAGE: "{display_term}: {definition}" 📍 Section 2 (Definitions), Pages 13-45

📝 EXPLANATION: Per Section 2 (Definitions) of the contract, **{display_term}** is defined as: {definition}

🔵 STATUS: CLEAR - The contract explicitly defines this term in Section 2.

⚡ Instant answer from contract definitions (no API cost)

⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

    return answer

def tier1_instant_answer(question_lower):
    """
    Check if a question can be answered instantly without API call.
    Returns (answer, status, response_time) or None if not a Tier 1 question.
    """
    start = time.time()

    # --- PAY RATE QUESTIONS ---
    pay_keywords = ['pay rate', 'hourly rate', 'make per hour', 'paid per hour',
                    'how much', 'what rate', 'what is the rate', 'what\'s the rate',
                    'captain rate', 'fo rate', 'first officer rate', 'captain pay',
                    'fo pay', 'first officer pay', 'pay scale']

    if any(kw in question_lower for kw in pay_keywords):
        parsed = _parse_pay_question(question_lower)
        if parsed:
            aircraft, position, year = parsed
            answer = _format_pay_answer(aircraft, position, year)
            return answer, 'CLEAR', round(time.time() - start, 1)

    # Also catch "year X captain/FO" patterns even without explicit pay keywords
    if re.search(r'year\s*\d{1,2}\s*(captain|capt|first officer|fo |f/o)', question_lower) or \
       re.search(r'\d{1,2}[\s-]*year\s*(captain|capt|first officer|fo |f/o)', question_lower):
        parsed = _parse_pay_question(question_lower)
        if parsed:
            aircraft, position, year = parsed
            answer = _format_pay_answer(aircraft, position, year)
            return answer, 'CLEAR', round(time.time() - start, 1)

    # --- DEFINITION QUESTIONS ---
    def_patterns = [
        r'what (?:does|is|are|do)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*(?:mean|stand for|definition)',
        r'define\s+["\']?(.+?)["\']?\s*$',
        r'what (?:is|are)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*(?:in the contract|per the contract|according to)',
        r'what (?:is|are)\s+(?:a |an |the )?["\']?(.+?)["\']?\s*\??\s*$',
    ]

    for pattern in def_patterns:
        match = re.search(pattern, question_lower.strip().rstrip('?'))
        if match:
            term = match.group(1).strip().lower()
            # Remove trailing words that aren't part of the term
            term = re.sub(r'\s+(mean|means|stand|stands|defined|definition).*$', '', term)
            if term in DEFINITIONS_LOOKUP:
                answer = _format_definition_answer(term, DEFINITIONS_LOOKUP[term])
                return answer, 'CLEAR', round(time.time() - start, 1)
            # Try partial match for multi-word terms
            for def_term, definition in DEFINITIONS_LOOKUP.items():
                if term == def_term or (len(term) > 3 and term in def_term):
                    answer = _format_definition_answer(def_term, definition)
                    return answer, 'CLEAR', round(time.time() - start, 1)

    return None

# ============================================================
# MAIN ENTRY
# ============================================================
def ask_question(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history=None):
    normalized = question.strip().lower()

    # Tier 1: Instant answers — no API cost, no embedding cost
    tier1_result = tier1_instant_answer(normalized)
    if tier1_result is not None:
        return tier1_result

    # Always check cache first — regardless of conversation history
    question_embedding = get_embedding_cached(normalized, openai_client)
    semantic_cache = get_semantic_cache()
    cached_result = semantic_cache.lookup(question_embedding, contract_id)
    if cached_result is not None:
        return cached_result

    answer, status, response_time = _ask_question_api(
        normalized, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history
    )

    # Always store in cache
    semantic_cache.store(question_embedding, normalized, answer, status, response_time, contract_id)

    return answer, status, response_time

# ============================================================
# SESSION STATE
# ============================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'selected_contract' not in st.session_state:
    st.session_state.selected_contract = None
if 'show_reference' not in st.session_state:
    st.session_state.show_reference = None
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}

# ============================================================
# LOGIN
# ============================================================
if not st.session_state.authenticated:
    st.title("✈️ AskTheContract - Beta Access")
    st.write("**AI-Powered Contract Q&A for Pilots**")

    with st.form("login_form"):
        password = st.text_input("Enter beta password:", type="password")
        submitted = st.form_submit_button("Login", type="primary")
        if submitted:
            try:
                correct_password = st.secrets["APP_PASSWORD"]
            except:
                correct_password = "nacpilot2026"
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password. Contact the developer for access.")
    st.info("🔒 This is a beta test version.")

# ============================================================
# MAIN APP
# ============================================================
else:
    st.title("✈️ AskTheContract")
    st.caption("AI-Powered Contract Q&A System")

    # ---- SIDEBAR ----
    with st.sidebar:
        st.header("Contract Selection")
        manager = init_contract_manager()
        available_contracts = manager.get_available_contracts()

        contract_options = {
            info['airline_name']: contract_id
            for contract_id, info in available_contracts.items()
        }

        selected_name = st.selectbox(
            "Select your airline:",
            options=list(contract_options.keys())
        )
        selected_contract_id = contract_options[selected_name]

        if st.session_state.selected_contract != selected_contract_id:
            st.session_state.selected_contract = selected_contract_id
            st.session_state.conversation = []

        contract_info = manager.get_contract_info(selected_contract_id)
        airline_name = contract_info['airline_name']

        st.info(f"""
        **{airline_name}**

        📄 Pages: {contract_info['total_pages']}

        📅 Version: {contract_info['contract_version']}
        """)

        st.write("---")

        # FEATURE 1: Quick Reference Cards
        st.subheader("📖 Quick Reference")
        st.caption("Zero AI — loads instantly")
        for card_name, card_data in QUICK_REFERENCE_CARDS.items():
            if st.button(f"{card_data['icon']} {card_name}", key=f"ref_{card_name}", use_container_width=True):
                st.session_state.show_reference = card_name

        st.write("---")
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.conversation = []
            st.session_state.show_reference = None
            st.rerun()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # ---- MAIN CONTENT ----
    st.info(f"📋 This tool searches **only** the **{airline_name} Pilot Contract (JCBA)**. It does not cover FAA regulations (FARs), Company Operations Manuals, or other policies.")

    # Show Quick Reference Card if selected
    if st.session_state.show_reference:
        card = QUICK_REFERENCE_CARDS[st.session_state.show_reference]
        st.markdown(card['content'])
        if st.button("✖ Close Reference Card"):
            st.session_state.show_reference = None
            st.rerun()
        st.write("---")

    # Question input
    with st.form(key="question_form", clear_on_submit=True):
        question = st.text_input(
            "Ask a question about your contract:",
            placeholder="Example: What is the daily pay guarantee?"
        )
        submit_button = st.form_submit_button("Ask", type="primary")

    if submit_button and question:
        st.session_state.show_reference = None

        with st.spinner("Searching contract..."):
            chunks, embeddings = load_contract(st.session_state.selected_contract)
            openai_client, anthropic_client = init_clients()
            history = st.session_state.conversation if st.session_state.conversation else None

            answer, status, response_time = ask_question(
                question, chunks, embeddings,
                openai_client, anthropic_client,
                st.session_state.selected_contract,
                airline_name, history
            )

            category = classify_question(question)

            logger = init_logger()
            logger.log_question(
                question_text=question,
                answer_text=answer,
                status=status,
                contract_id=st.session_state.selected_contract,
                response_time=response_time
            )

            st.session_state.conversation.append({
                'question': question,
                'answer': answer,
                'status': status,
                'category': category,
                'response_time': round(response_time, 1)
            })

    # ---- CONVERSATION HISTORY ----
    if st.session_state.conversation:
        st.write("---")

        for i, qa in enumerate(reversed(st.session_state.conversation)):
            q_num = len(st.session_state.conversation) - i

            st.markdown(f"### Q{q_num}: {qa['question']}")

            # FEATURE 2: Canonical Question Label
            category = qa.get('category', classify_question(qa['question']))
            st.caption(f"📂 Question type: {category}  •  ⏱️ Answered in {qa.get('response_time', '?')}s")

            # Answer with status color
            if qa['status'] == 'CLEAR':
                st.success(qa['answer'])
            elif qa['status'] == 'AMBIGUOUS':
                st.warning(qa['answer'])
            else:
                st.info(qa['answer'])

            # FEATURE 3: "What Would Change This Answer?"
            with st.expander("⚙️ What would change this answer?"):
                st.markdown(get_answer_modifier(category))

            # Bottom row
            col1, col2, col3, col4 = st.columns([1, 1, 3, 1])

            # FEATURE 4: Answer Rating
            rating_key = f"rating_{q_num}"
            with col1:
                if st.button("👍", key=f"up_{q_num}"):
                    log_rating(qa['question'], "up")
                    st.session_state.ratings[rating_key] = "up"
            with col2:
                if st.button("👎", key=f"down_{q_num}"):
                    log_rating(qa['question'], "down")
                    st.session_state.ratings[rating_key] = "down"
            with col3:
                if rating_key in st.session_state.ratings:
                    r = st.session_state.ratings[rating_key]
                    st.caption("✅ Thanks for your feedback!" if r == "up" else "📝 Thanks — we'll review this answer.")

            # FEATURE 5: Copy / Export Answer
            copy_text = f"""Question: {qa['question']}
Category: {category}
Status: {qa['status']}

{qa['answer']}

---
Generated by AskTheContract | {airline_name} JCBA
This is not legal advice."""

            with st.expander("📋 Copy / Export Answer"):
                st.code(copy_text, language=None)
                st.caption("Select all text above → Ctrl+C (or Cmd+C on Mac)")

            st.write("---")

    # ---- FOOTER ----
    st.caption("⚠️ **Disclaimer:** This tool searches only the pilot union contract (JCBA). It does not cover FAA regulations, company manuals, or other policies. This is not legal advice. Consult your union representative.")
