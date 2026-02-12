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
import re
import math

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

**Current Hourly Rate = DOS Rate × 1.14869** (7 annual 2% increases since July 2018)

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
    "Reserve → Types & Definitions": ['reserve type', 'reserve duty', 'reserve rules', 'reserve', 'r-1', 'r-2', 'r-3', 'r-4', 'what is reserve'],
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
    "Expenses / Per Diem": ['per diem', 'meal allowance', 'meal money', 'hotel', 'lodging', 'expenses', 'transportation', 'parking'],
    "Sick Leave": ['sick', 'sick call', 'sick leave', 'calling in sick', 'illness', 'sick pay', 'sick bank'],
    "Deadhead": ['deadhead', 'deadhead pay', 'deadhead rest', 'positioning', 'repositioning'],
    "Hours of Service": ['hours of service', 'flight time limit', 'block limit', 'rest interruption', 'rest interrupted'],
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

def log_rating(question_text, rating, contract_id, comment=""):
    """Log a rating via ContractLogger (Turso-backed)."""
    try:
        logger = init_logger()
        logger.log_rating(question_text, rating, contract_id, comment)
        return True
    except:
        return False

# ============================================================
# SEMANTIC SIMILARITY CACHE
# ============================================================
class SemanticCache:
    """Turso-backed persistent cache with in-memory similarity search.
    
    Uses Turso HTTP API — no extra packages needed.
    On startup: loads all cached Q&A from Turso into memory.
    On new answer: writes to both memory AND Turso.
    On restart/deploy: memory reloads from Turso — nothing lost.
    Falls back to memory-only if Turso is unavailable.
    """
    SIMILARITY_THRESHOLD = 0.93
    MAX_ENTRIES = 2000

    def __init__(self):
        self._lock = threading.Lock()
        self._entries = {}
        self._turso_available = False
        turso_url = os.environ.get('TURSO_DATABASE_URL', '')
        self._turso_token = os.environ.get('TURSO_AUTH_TOKEN', '')
        # Convert libsql:// URL to https:// for HTTP API
        if turso_url and self._turso_token:
            self._http_url = turso_url.replace('libsql://', 'https://') + '/v3/pipeline'
            self._init_turso()
        else:
            self._http_url = ''
            print("[Cache] No Turso credentials — memory-only mode")

    def _turso_request(self, statements):
        """Send SQL statements to Turso via HTTP API."""
        import urllib.request
        import base64 as b64module
        requests_body = []
        for stmt in statements:
            if isinstance(stmt, str):
                requests_body.append({"type": "execute", "stmt": {"sql": stmt}})
            elif isinstance(stmt, dict):
                requests_body.append({"type": "execute", "stmt": stmt})
        requests_body.append({"type": "close"})
        
        data = json.dumps({"requests": requests_body}).encode('utf-8')
        req = urllib.request.Request(
            self._http_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self._turso_token}'
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.request.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else 'no body'
            print(f"[Cache] Turso HTTP {e.code}: {error_body[:200]}")
            return None
        except Exception as e:
            print(f"[Cache] Turso error: {e}")
            return None

    def _init_turso(self):
        """Initialize Turso table via HTTP API."""
        try:
            result = self._turso_request([
                """CREATE TABLE IF NOT EXISTS answer_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    status TEXT,
                    response_time REAL,
                    embedding_b64 TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                "CREATE INDEX IF NOT EXISTS idx_cache_contract ON answer_cache(contract_id)"
            ])
            if result:
                self._turso_available = True
                self._load_from_turso()
                total = sum(len(v) for v in self._entries.values())
                print(f"[Cache] ✅ Turso connected — loaded {total} cached answers")
            else:
                print("[Cache] Turso init failed — memory-only mode")
        except Exception as e:
            print(f"[Cache] Turso init error: {e} — memory-only mode")

    def _load_from_turso(self):
        """Load all cached entries from Turso into memory."""
        if not self._turso_available:
            return
        import base64 as b64module
        try:
            result = self._turso_request([
                "SELECT contract_id, question, answer, status, response_time, embedding_b64 FROM answer_cache ORDER BY created_at DESC"
            ])
            if not result or 'results' not in result:
                return
            # Parse response — results[0] is our SELECT
            select_result = result['results'][0]
            if select_result.get('type') != 'ok':
                return
            rows = select_result['response']['result'].get('rows', [])
            for row in rows:
                contract_id = row[0]['value']
                question = row[1]['value']
                answer = row[2]['value']
                status = row[3]['value'] if row[3]['type'] != 'null' else ''
                response_time = float(row[4]['value']) if row[4]['type'] != 'null' else 0.0
                emb_b64 = row[5]['value']
                embedding = np.frombuffer(b64module.b64decode(emb_b64), dtype=np.float32)
                if contract_id not in self._entries:
                    self._entries[contract_id] = []
                if len(self._entries[contract_id]) < self.MAX_ENTRIES:
                    self._entries[contract_id].append((embedding, question, answer, status, response_time))
        except Exception as e:
            print(f"[Cache] Failed to load from Turso: {e}")

    def _save_to_turso(self, embedding, question, answer, status, response_time, contract_id):
        """Persist a new cache entry to Turso via HTTP API."""
        if not self._turso_available:
            return
        import base64 as b64module
        try:
            emb_b64 = b64module.b64encode(np.array(embedding, dtype=np.float32).tobytes()).decode('ascii')
            stmt = {
                "sql": "INSERT INTO answer_cache (contract_id, question, answer, status, response_time, embedding_b64) VALUES (?, ?, ?, ?, ?, ?)",
                "args": [
                    {"type": "text", "value": contract_id},
                    {"type": "text", "value": question},
                    {"type": "text", "value": answer},
                    {"type": "text", "value": status or ""},
                    {"type": "float", "value": response_time},
                    {"type": "text", "value": emb_b64}
                ]
            }
            self._turso_request([stmt])
        except Exception as e:
            print(f"[Cache] Failed to save to Turso: {e}")

    def lookup(self, embedding, contract_id):
        embedding = np.array(embedding, dtype=np.float32)
        with self._lock:
            entries = self._entries.get(contract_id, [])
            best_score = 0
            best_result = None
            for cached_emb, cached_q, cached_answer, cached_status, cached_time in entries:
                score = np.dot(embedding, cached_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(cached_emb)
                )
                if score > self.SIMILARITY_THRESHOLD and score > best_score:
                    best_score = score
                    best_result = (cached_answer, cached_status, cached_time)
            return best_result

    def store(self, embedding, question, answer, status, response_time, contract_id):
        embedding = np.array(embedding, dtype=np.float32)
        with self._lock:
            if contract_id not in self._entries:
                self._entries[contract_id] = []
            entries = self._entries[contract_id]
            for cached_emb, _, _, _, _ in entries:
                score = np.dot(embedding, cached_emb) / (
                    np.linalg.norm(embedding) * np.linalg.norm(cached_emb)
                )
                if score > self.SIMILARITY_THRESHOLD:
                    return
            if len(entries) >= self.MAX_ENTRIES:
                entries.pop(0)
            entries.append((embedding, question, answer, status, response_time))
        self._save_to_turso(embedding, question, answer, status, response_time, contract_id)

    def clear(self, contract_id=None):
        with self._lock:
            if contract_id:
                self._entries.pop(contract_id, None)
            else:
                self._entries = {}
        if self._turso_available:
            try:
                if contract_id:
                    stmt = {
                        "sql": "DELETE FROM answer_cache WHERE contract_id = ?",
                        "args": [{"type": "text", "value": contract_id}]
                    }
                else:
                    stmt = "DELETE FROM answer_cache"
                self._turso_request([stmt])
            except Exception as e:
                print(f"[Cache] Failed to clear Turso: {e}")

    def stats(self):
        total = sum(len(v) for v in self._entries.values())
        return {
            'total_entries': total,
            'turso_connected': self._turso_available,
            'contracts': {k: len(v) for k, v in self._entries.items()}
        }

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

# ============================================================
# BM25 KEYWORD SEARCH
# Catches exact contract terms that embeddings might miss.
# No external packages — pure Python implementation.
# ============================================================
# Contract-specific stopwords — common English words plus filler
_BM25_STOPWORDS = frozenset([
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'about', 'between',
    'through', 'after', 'before', 'during', 'and', 'or', 'but', 'not',
    'no', 'nor', 'if', 'then', 'than', 'that', 'this', 'these', 'those',
    'it', 'its', 'he', 'his', 'him', 'i', 'my', 'me', 'we', 'our',
    'you', 'your', 'they', 'their', 'what', 'which', 'who', 'when',
    'where', 'how', 'all', 'each', 'any', 'both', 'such', 'other',
])

def _bm25_tokenize(text):
    """Tokenize text for BM25. Preserves section numbers and hyphenated terms."""
    # Lowercase, split on whitespace and punctuation but keep hyphens and dots in terms
    tokens = re.findall(r'[a-z0-9](?:[a-z0-9\-\.]*[a-z0-9])?', text.lower())
    return [t for t in tokens if t not in _BM25_STOPWORDS and len(t) > 1]

@st.cache_data(show_spinner=False)
def _build_bm25_index(_chunk_texts):
    """Pre-compute BM25 index from chunk texts. Cached so it only runs once."""
    # _chunk_texts is a tuple of strings (hashable for st.cache_data)
    doc_tokens = [_bm25_tokenize(text) for text in _chunk_texts]
    doc_count = len(doc_tokens)
    avg_dl = sum(len(d) for d in doc_tokens) / doc_count if doc_count > 0 else 1

    # Document frequency: how many docs contain each term
    df = {}
    for tokens in doc_tokens:
        for term in set(tokens):
            df[term] = df.get(term, 0) + 1

    # IDF: log((N - df + 0.5) / (df + 0.5) + 1)
    idf = {}
    for term, freq in df.items():
        idf[term] = math.log((doc_count - freq + 0.5) / (freq + 0.5) + 1)

    return doc_tokens, idf, avg_dl

def _bm25_search(query, chunks, top_n=15, k1=1.5, b=0.75):
    """Score all chunks against query using BM25. Returns top_n (score, chunk) pairs."""
    # Build index (cached after first call)
    chunk_texts = tuple(c['text'] for c in chunks)
    doc_tokens, idf, avg_dl = _build_bm25_index(chunk_texts)

    query_tokens = _bm25_tokenize(query)
    if not query_tokens:
        return []

    scores = []
    for i, tokens in enumerate(doc_tokens):
        dl = len(tokens)
        score = 0.0
        # Term frequency map for this doc
        tf_map = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        for qt in query_tokens:
            if qt in tf_map:
                tf = tf_map[qt]
                term_idf = idf.get(qt, 0)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * dl / avg_dl)
                score += term_idf * numerator / denominator

        if score > 0:
            scores.append((score, chunks[i]))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_n]

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

# ============================================================
# CONTEXT PACKS — Curated essential pages per topic
# Guarantees the right provisions are always included.
# Embedding search supplements with anything unusual.
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

# Provision chains: keyword triggers → supplemental LOA/MOU pages
# These fire regardless of pack category to catch cross-references
PROVISION_CHAINS = {
    # Check Airman / Instructor topics → all Check Airman LOA/MOU pages
    'check airman': [322, 323, 338, 339, 390, 392],
    'instructor pilot': [322, 323, 338, 339, 390, 392],
    'apd': [322, 323, 338, 339, 390, 392],
    'ghost bid': [322, 323, 338, 339],
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

def get_pack_chunks(pack_key, all_chunks):
    """Get all chunks from a context pack's essential pages."""
    if pack_key not in CONTEXT_PACKS:
        return []
    pages = set(CONTEXT_PACKS[pack_key]['pages'])
    return [c for c in all_chunks if c['page'] in pages]

def classify_all_matching_packs(question_text):
    """Return all pack keys that match the question, ordered by match strength."""
    q_lower = question_text.lower()
    pack_scores = {}  # pack_key -> match count

    for category, keywords in QUESTION_CATEGORIES.items():
        count = sum(1 for kw in keywords if kw in q_lower)
        if count > 0:
            pack_key = CATEGORY_TO_PACK.get(category)
            if pack_key and pack_key in CONTEXT_PACKS:
                pack_scores[pack_key] = max(pack_scores.get(pack_key, 0), count)

    # Sort by match strength descending
    sorted_packs = sorted(pack_scores.items(), key=lambda x: x[1], reverse=True)
    return [pk for pk, _ in sorted_packs]

def search_contract(question, chunks, embeddings, openai_client, max_chunks=75):
    question_embedding = get_embedding_cached(question, openai_client)
    question_lower = question.lower()
    forced_chunks = find_force_include_chunks(question_lower, chunks)

    # Cross-topic pack detection — find ALL matching packs
    matching_packs = classify_all_matching_packs(question)

    if matching_packs:
        # Merge pages from all matching packs
        merged_pages = set()
        for pk in matching_packs:
            merged_pages.update(CONTEXT_PACKS[pk]['pages'])

        # Provision chain injection — add LOA/MOU pages triggered by keywords
        chain_hits = []
        for keyword, chain_pages in PROVISION_CHAINS.items():
            if keyword in question_lower:
                merged_pages.update(chain_pages)
                chain_hits.append(keyword)

        pack_chunks = [c for c in chunks if c['page'] in merged_pages]
        print(f"[Search] PACK MODE: {matching_packs} | chains: {chain_hits} | pages: {len(merged_pages)} | chunks: {len(pack_chunks)}")

        # Multi-pack gets slightly higher cap; single pack stays at 30
        if len(matching_packs) > 1:
            max_total = 35
            embedding_top_n = 10
        else:
            max_total = CONTEXT_PACKS[matching_packs[0]].get('max_total', 30)
            embedding_top_n = CONTEXT_PACKS[matching_packs[0]].get('embedding_top_n', 15)

        # Rank pack chunks by relevance and trim
        max_pack = max_total - min(embedding_top_n, 5)
        if len(pack_chunks) > max_pack:
            # Build chunk ID → index lookup once
            id_to_idx = {c.get('id'): i for i, c in enumerate(chunks)}
            pack_scores = []
            for pc in pack_chunks:
                idx = id_to_idx.get(pc.get('id'))
                if idx is not None:
                    score = cosine_similarity(question_embedding, embeddings[idx])
                else:
                    score = 0
                pack_scores.append((score, pc))
            pack_scores.sort(reverse=True, key=lambda x: x[0])
            pack_chunks = [pc for _, pc in pack_scores[:max_pack]]
    else:
        # FALLBACK MODE: pure embedding search (General questions)
        # But still check provision chains for keyword-triggered pages
        chain_pages = set()
        chain_hits = []
        for keyword, pages in PROVISION_CHAINS.items():
            if keyword in question_lower:
                chain_pages.update(pages)
                chain_hits.append(keyword)
        if chain_pages:
            pack_chunks = [c for c in chunks if c['page'] in chain_pages]
            print(f"[Search] FALLBACK + CHAINS: {chain_hits} | pages: {len(chain_pages)} | chunks: {len(pack_chunks)}")
        else:
            pack_chunks = []
            print(f"[Search] FALLBACK — no packs, no chains matched")
        embedding_top_n = 30
        max_total = 30

    # Embedding search
    similarities = []
    for i, chunk_embedding in enumerate(embeddings):
        score = cosine_similarity(question_embedding, chunk_embedding)
        similarities.append((score, chunks[i]))
    similarities.sort(reverse=True, key=lambda x: x[0])
    embedding_chunks = [chunk for score, chunk in similarities[:embedding_top_n]]

    # BM25 keyword search — catches exact terms embeddings miss
    bm25_top_n = min(10, embedding_top_n)
    bm25_results = _bm25_search(question, chunks, top_n=bm25_top_n)
    bm25_chunks = [chunk for score, chunk in bm25_results]

    # Merge: forced first, then pack, then BM25, then embedding — deduplicated
    seen_ids = set()
    merged = []

    for chunk in forced_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)

    for chunk in pack_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_total:
                break

    for chunk in bm25_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_total:
                break

    for chunk in embedding_chunks:
        chunk_id = chunk.get('id', f"{chunk['page']}_{chunk['text'][:50]}")
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            merged.append(chunk)
            if len(merged) >= max_total:
                break

    # Log final result
    pages_sent = sorted(set(c['page'] for c in merged))
    print(f"[Search] FINAL: {len(merged)} chunks from pages {pages_sent[:15]}{'...' if len(pages_sent) > 15 else ''}")

    return merged

# ============================================================
# PRE-COMPUTED PAY CALCULATOR
# Extracts scenario details, does all math locally, injects
# results into API call so Sonnet explains — never calculates.
# ============================================================
def _build_pay_reference(question):
    """Extract pay scenario details and pre-compute all applicable pay values.
    Returns a text block to inject into the API call, or empty string."""
    q = question.lower()

    # Only trigger for pay-related questions
    pay_triggers = ['pay', 'paid', 'compensation', 'make', 'earn', 'rate', 'rig',
                    'dpg', 'premium', 'overtime', 'pch', 'wage', 'salary',
                    'junior assignment', 'ja ', 'open time', 'day off']
    if not any(t in q for t in pay_triggers):
        return ""

    # Extract position
    if 'captain' in q or 'capt ' in q:
        positions = ['Captain']
    elif 'first officer' in q or 'fo ' in q or 'f/o' in q:
        positions = ['First Officer']
    else:
        positions = ['Captain', 'First Officer']

    # Extract year
    year_match = re.search(r'year\s*(\d{1,2})', q)
    if not year_match:
        year_match = re.search(r'(\d{1,2})[\s-]*year', q)
    year = int(year_match.group(1)) if year_match and 1 <= int(year_match.group(1)) <= 12 else None

    # Extract numeric values for duty hours, block time, TAFD
    duty_hours = None
    block_hours = None
    tafd_hours = None

    # "12 hour duty" or "duty of 12 hours" or "12-hour duty day" or "duty for 12 hours"
    duty_match = re.search(r'(\d+(?:\.\d+)?)\s*[\s-]*hours?\s*(?:of\s+)?(?:duty|on duty|duty day|duty period)', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:of|for|period|day|time)?\s*(?:of|is|was|for|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:went|reached|hit|got|exceeded|was)\s*(?:to|up to)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if duty_match:
        duty_hours = float(duty_match.group(1))

    # "block time of 5 hours" or "5 hours of block" or "flew 5 hours"
    block_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:of\s+)?(?:block|flight|flying|flew)', q)
    if not block_match:
        block_match = re.search(r'(?:block|flight|flew)\s*(?:time)?\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if block_match:
        block_hours = float(block_match.group(1))

    # "TAFD of 24 hours" or "24 hours TAFD" or "away from domicile for 24 hours"
    tafd_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:tafd|away from domicile|time away)', q)
    if not tafd_match:
        tafd_match = re.search(r'(?:tafd|time away|away from domicile)\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if tafd_match:
        tafd_hours = float(tafd_match.group(1))

    # Detect premium scenarios
    premiums = {}
    if 'junior assign' in q or 'ja ' in q or ' ja' in q:
        premiums['Junior Assignment 1st in 3mo (200%)'] = 2.00
        premiums['Junior Assignment 2nd in 3mo (250%)'] = 2.50
    if 'open time' in q and ('pick' in q or 'award' in q or 'volunt' in q):
        premiums['Open Time Pickup (150%)'] = 1.50
    if 'vacation' in q and ('cancel' in q or 'work' in q):
        premiums['Vacation Cancellation Work (200%)'] = 2.00
    if 'check airman' in q or 'instructor' in q or 'apd' in q:
        if 'day off' in q or 'day-off' in q:
            premiums['Check Airman Admin on Day Off (175%)'] = 1.75
    if 'hostile' in q:
        premiums['Hostile Area (200%)'] = 2.00

    # If we have no year and no numeric values, just provide rate table reference
    has_scenario = duty_hours or block_hours or tafd_hours
    if not year and not has_scenario:
        return ""

    # Build the reference
    lines = ["PRE-COMPUTED PAY REFERENCE (use these exact numbers — do not recalculate):"]
    lines.append(f"Current pay multiplier: DOS rate x 1.02^{PAY_INCREASES} = DOS x {PAY_MULTIPLIER:.5f}")
    lines.append("")

    # Show rates for applicable positions
    years_to_show = [year] if year else list(range(1, 13))
    for pos in positions:
        for y in years_to_show:
            dos = PAY_RATES_DOS['B737'][pos][y]
            current = round(dos * PAY_MULTIPLIER, 2)
            lines.append(f"B737 {pos} Year {y}: DOS {dos:.2f} → Current {current:.2f}/hour")

    # If scenario has numbers, compute all pay guarantees
    if has_scenario and year:
        lines.append("")
        lines.append("PAY CALCULATIONS FOR THIS SCENARIO:")
        for pos in positions:
            dos = PAY_RATES_DOS['B737'][pos][year]
            rate = round(dos * PAY_MULTIPLIER, 2)
            lines.append(f"  {pos} Year {year} rate: {rate:.2f}/hour")

            calcs = []

            if block_hours is not None:
                val = round(block_hours * rate, 2)
                calcs.append(f"    Block Time: {block_hours} PCH x {rate:.2f} = {val:.2f}")

            # DPG always applies
            dpg_val = round(3.82 * rate, 2)
            calcs.append(f"    DPG (minimum): 3.82 PCH x {rate:.2f} = {dpg_val:.2f}")

            if duty_hours is not None:
                rig_pch = round(duty_hours / 2, 2)
                rig_val = round(rig_pch * rate, 2)
                calcs.append(f"    Duty Rig: {duty_hours} hrs / 2 = {rig_pch} PCH x {rate:.2f} = {rig_val:.2f}")

            if tafd_hours is not None:
                trip_pch = round(tafd_hours / 4.9, 2)
                trip_val = round(trip_pch * rate, 2)
                calcs.append(f"    Trip Rig: {tafd_hours} hrs / 4.9 = {trip_pch} PCH x {rate:.2f} = {trip_val:.2f}")

            # Determine greatest PCH
            pch_values = {'DPG': 3.82}
            if block_hours is not None:
                pch_values['Block Time'] = block_hours
            if duty_hours is not None:
                pch_values['Duty Rig'] = round(duty_hours / 2, 2)
            if tafd_hours is not None:
                pch_values['Trip Rig'] = round(tafd_hours / 4.9, 2)

            best_name = max(pch_values, key=pch_values.get)
            best_pch = pch_values[best_name]
            best_pay = round(best_pch * rate, 2)

            for c in calcs:
                lines.append(c)
            lines.append(f"    → GREATEST: {best_name} = {best_pch} PCH = {best_pay:.2f} at 100%")

            # Apply premiums
            if premiums:
                lines.append("")
                lines.append("    WITH PREMIUMS:")
                for prem_name, mult in premiums.items():
                    prem_pay = round(best_pch * rate * mult, 2)
                    lines.append(f"    {prem_name}: {best_pch} PCH x {rate:.2f} x {mult} = {prem_pay:.2f}")

            lines.append("")

    return "\n".join(lines)

# ============================================================
# GRIEVANCE PATTERN DETECTOR
# Scans question for potential contract violation indicators
# and injects alerts so Sonnet addresses them proactively.
# ============================================================
def _detect_grievance_patterns(question):
    """Detect potential contract violation patterns in a scenario question.
    Returns a text block to inject into the API call, or empty string."""
    q = question.lower()
    alerts = []

    # --- DUTY TIME VIOLATIONS ---
    duty_match = re.search(r'(\d+(?:\.\d+)?)\s*[\s-]*hours?\s*(?:of\s+)?(?:duty|on duty|duty day|duty period)', q)
    if not duty_match:
        duty_match = re.search(r'duty\s*(?:of|for|period|day|time)?\s*(?:of|is|was|for|:)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if not duty_match:
        # "duty went to 15.5 hours" / "duty reached 17 hours" / "duty hit 16 hours"
        duty_match = re.search(r'duty\s*(?:went|reached|hit|got|exceeded|was)\s*(?:to|up to)?\s*(\d+(?:\.\d+)?)\s*hours?', q)
    if duty_match:
        duty_hrs = float(duty_match.group(1))
        if duty_hrs > 16:
            alerts.append(f"⚠️ DUTY TIME ALERT: {duty_hrs} hours exceeds the 16-hour maximum for a basic 2-pilot crew (Section 13.F.1). Verify crew complement — 18hr max for augmented (3-pilot), 20hr max for heavy (4-pilot). If exceeded, per Section 14.N, the Company must remove the pilot from the trip and place into rest.")
        elif duty_hrs > 14:
            alerts.append(f"⚠️ REST REQUIREMENT ALERT: {duty_hrs} hours of duty triggers the 12-hour minimum rest requirement (Section 13.G.1 — duty over 14 hours requires 12 hours rest, not the standard 10 hours).")

    # --- REST PERIOD VIOLATIONS ---
    rest_match = re.search(r'(\d+(?:\.\d+)?)\s*hours?\s*(?:of\s+)?(?:rest|off|between)', q)
    if rest_match:
        rest_hrs = float(rest_match.group(1))
        if rest_hrs < 10:
            alerts.append(f"⚠️ REST VIOLATION ALERT: {rest_hrs} hours of rest is below the 10-hour minimum required after duty of 14 hours or less (Section 13.G.1). This is a potential grievance.")
        elif rest_hrs < 12:
            alerts.append(f"⚠️ REST ALERT: {rest_hrs} hours rest — verify prior duty period length. If prior duty exceeded 14 hours, minimum rest is 12 hours, not 10 (Section 13.G.1).")

    # --- JUNIOR ASSIGNMENT ISSUES ---
    if 'junior assign' in q or 'ja ' in q or ' ja' in q:
        alerts.append("⚠️ JA CHECKLIST: Verify (1) inverse seniority order was followed (Section 14.O.1), (2) whether this is 1st or 2nd JA in rolling 3-month period for premium rate (Section 3.R), (3) one-extension-per-month limit if extended (Section 14.N.6).")
        if 'day off' in q:
            alerts.append("⚠️ DAY-OFF JA: Per Section 14.O, JA on a Day Off requires 200% premium (1st in 3mo) or 250% (2nd in 3mo). Verify the pilot was not senior to other available pilots.")

    # --- EXTENSION ISSUES ---
    if 'extend' in q or 'extension' in q:
        alerts.append("⚠️ EXTENSION CHECKLIST: Per Section 14.N — (1) only ONE involuntary extension per month is permitted, (2) extension cannot violate duty time limits (Section 13.F), (3) extension cannot cause a pilot to miss a scheduled Day Off beyond 0200 LDT (Section 15.A.7).")

    # --- DAY OFF ENCROACHMENT ---
    if 'day off' in q and ('work' in q or 'called' in q or 'schedul' in q or 'assign' in q or 'duty' in q):
        if 'ja' not in q and 'junior' not in q:  # JA already handled above
            alerts.append("⚠️ DAY-OFF WORK: Determine if this was a Junior Assignment (200%/250% per Section 3.R) or voluntary Open Time pickup (150% per Section 3.P). Assignments may be scheduled up to 0200 LDT into a Day Off (Section 15.A.7) — duty past 0200 into a Day Off is a potential violation.")

    # --- MINIMUM DAYS OFF ---
    if 'days off' in q and ('month' in q or 'line' in q or 'schedule' in q):
        alerts.append("⚠️ DAYS OFF MINIMUM: Per Section 14.E.5.d, minimum is 13 Days Off for a 30-day month and 14 Days Off for a 31-day month. Verify the published line meets this requirement.")

    # --- POSITIVE CONTACT ---
    if 'schedule change' in q or 'reassign' in q or 'no call' in q or 'no contact' in q or 'never called' in q or 'text message' in q or 'text only' in q or 'email only' in q or 'voicemail' in q or ('no phone' in q and 'call' in q) or ('text' in q and 'no call' in q) or ('changed' in q and ('text' in q or 'email' in q)):
        alerts.append("⚠️ POSITIVE CONTACT REQUIRED: Per MOU #2 (Page 381), schedule changes require Positive Contact via the pilot's authorized phone number. Email, text, or voicemail alone is NOT sufficient — the pilot must acknowledge the change verbally. Failure to make Positive Contact means the change is not effective.")

    # --- REST INTERRUPTION ---
    if 'rest' in q and ('interrupt' in q or 'call' in q or 'phone' in q or 'woke' in q or 'disturb' in q):
        alerts.append("⚠️ REST INTERRUPTION: Per Section 13.H.7, if a pilot's rest is interrupted (e.g., hotel security, repeated phone calls), the required rest period begins anew. Only emergency/security notifications are exempt from this rule.")

    # --- REASSIGNMENT ISSUES ---
    if 'reassign' in q and ('reserve' in q or 'r-1' in q or 'r-2' in q or 'r-3' in q or 'r-4' in q or 'r1' in q or 'r2' in q):
        alerts.append("⚠️ RESERVE REASSIGNMENT: Per MOU #4 (Page 383), Crew Scheduling cannot reassign a pilot performing a Trip Pairing to a Reserve Assignment. Reserve type changes require 12-hour notice (MOU #4 provision 8). If more than 2 pilots may be reassigned, inverse seniority applies (MOU #4 provision 13).")

    if not alerts:
        return ""

    header = "GRIEVANCE PATTERN ALERTS (address each applicable alert in your response):"
    return header + "\n" + "\n".join(alerts)


# ============================================================
# API CALL
# ============================================================
# ============================================================
# QUESTION COMPLEXITY ROUTER
# Routes questions to the right model tier:
#   SIMPLE  → Haiku (cheapest, ~0.3¢/question)
#   STANDARD → Sonnet (balanced, ~3.4¢/question)
#   COMPLEX  → Opus (smartest, ~20¢/question)
# ============================================================

# Model strings for each tier
MODEL_TIERS = {
    'simple': 'claude-haiku-4-5-20251001',
    'standard': 'claude-sonnet-4-20250514',
    'complex': 'claude-opus-4-20250514',
}

# Indicators that a question is COMPLEX — needs Opus-level reasoning
_COMPLEX_INDICATORS = [
    # Pay scenarios with specific numbers
    'what do i get paid', 'what would i get paid', 'what should i get paid',
    'what am i owed', 'how much should i be paid', 'calculate my pay',
    # Duty crossing into day off (overtime scope disputes)
    'into my day off', 'into a day off', 'past my day off',
    'extended into', 'crossed into',
    # Multi-provision scenarios
    'extended and', 'junior assigned and', 'on reserve and',
    # Explicit ambiguity / grievance strength questions
    'is this a grievance', 'should i grieve', 'do i have a grievance',
    'contract violation', 'violated the contract', 'violate the contract',
    # Complex comparisons
    'difference between', 'compared to', 'which is better',
    'what are my options', 'what are all the',
]

# Indicators that a question is SIMPLE — Haiku can handle it
_SIMPLE_PATTERNS = [
    # Section/location lookups
    r'^what section (?:covers|talks about|addresses|is about)',
    r'^where (?:can i find|does it talk about|is the section)',
    r'^which section',
    r'^what page',
    # Simple yes/no contract questions
    r'^(?:does|is|can|are) (?:the contract|there a)',
    # Single-word definition lookups that didn't match Tier 1
    r'^what (?:is|are) (?:a |an |the )?[\w\s]{1,25}\??$',
]

_SIMPLE_COMPILED = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_PATTERNS]

def _classify_complexity(question_lower, matching_packs=None, has_pay_ref=False, has_grievance_ref=False, conversation_history=None):
    """Classify question complexity for model routing.
    
    Returns: 'simple', 'standard', or 'complex'
    """
    # --- COMPLEX CHECKS (most expensive model, most reasoning needed) ---
    
    # 1. Multiple scenario indicators with numbers = complex pay calculation
    scenario_count = 0
    scenario_keywords = ['duty', 'block', 'flew', 'hours', 'day off', 'overtime',
                         'extension', 'junior assign', 'reserve', 'rap']
    for kw in scenario_keywords:
        if kw in question_lower:
            scenario_count += 1
    has_numbers = bool(re.search(r'\d+(?:\.\d+)?\s*(?:hours?|hr|pch|am|pm)', question_lower))
    has_times = bool(re.search(r'\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)|noon|midnight|\d{4}\s*(?:ldt|local|zulu)', question_lower))
    
    # Scenario with numbers AND multiple topics = complex
    if has_numbers and scenario_count >= 2:
        return 'complex'
    
    # Time references with pay/overtime = complex
    if has_times and any(kw in question_lower for kw in ['pay', 'paid', 'overtime', 'premium', 'owed']):
        return 'complex'
    
    # 2. Explicit complex indicators
    if any(ind in question_lower for ind in _COMPLEX_INDICATORS):
        return 'complex'
    
    # 3. Pre-computed pay reference fired AND grievance pattern fired = complex
    if has_pay_ref and has_grievance_ref:
        return 'complex'
    
    # 4. Cross-topic questions (multiple context packs matched)
    if matching_packs and len(matching_packs) >= 2:
        # Multi-pack + numbers = definitely complex
        if has_numbers or has_times:
            return 'complex'
        # Multi-pack without numbers = standard (e.g., "tell me about reserve and scheduling")
        return 'standard'
    
    # 5. Follow-up on a complex conversation — only if this looks like a follow-up
    if conversation_history and len(conversation_history) >= 2:
        last_answer = conversation_history[-1].get('answer', '')
        if 'AMBIGUOUS' in last_answer or 'OVERTIME SCOPE DISPUTE' in last_answer:
            # Only escalate if this looks like a follow-up (short, uses follow-up language)
            follow_up_signals = ['what if', 'what about', 'and if', 'but what if',
                                 'in that case', 'same scenario', 'same situation',
                                 'follow up', 'followup', 'you said', 'you mentioned',
                                 'what would change', 'does that mean']
            is_short = len(question_lower.split()) <= 15
            has_follow_up = any(sig in question_lower for sig in follow_up_signals)
            if is_short and has_follow_up:
                return 'complex'
    
    # --- SIMPLE CHECKS (cheapest model) ---
    
    # Short questions with simple patterns
    if len(question_lower.split()) <= 10:
        for pattern in _SIMPLE_COMPILED:
            if pattern.search(question_lower):
                return 'simple'
    
    # Single topic, no numbers, no scenarios = simple
    if scenario_count == 0 and not has_numbers and not has_times:
        if not has_pay_ref and not has_grievance_ref:
            # Very short questions are usually simple lookups
            if len(question_lower.split()) <= 8:
                return 'simple'
    
    # --- DEFAULT: STANDARD ---
    return 'standard'


def _ask_question_api(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history=None):
    start_time = time.time()

    relevant_chunks = search_contract(question, chunks, embeddings, openai_client)

    context_parts = []
    for chunk in relevant_chunks:
        section_info = chunk.get('section', 'Unknown Section')
        aircraft_info = f", Aircraft: {chunk['aircraft_type']}" if chunk.get('aircraft_type') else ""
        context_parts.append(f"[Page {chunk['page']}, {section_info}{aircraft_info}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    # Detect pay and grievance references (needed for routing AND injection)
    pay_ref = _build_pay_reference(question)
    grievance_ref = _detect_grievance_patterns(question)

    # Route question to the right model tier
    matching_packs = classify_all_matching_packs(question)
    model_tier = _classify_complexity(
        question.lower(),
        matching_packs=matching_packs,
        has_pay_ref=bool(pay_ref),
        has_grievance_ref=bool(grievance_ref),
        conversation_history=conversation_history,
    )
    model_name = MODEL_TIERS[model_tier]

    # Detect if pay-related content is needed (used for prompt trimming and logging)
    q_lower = question.lower()
    is_pay_question = any(kw in q_lower for kw in [
        'pay', 'paid', 'compensation', 'wage', 'salary', 'rate', 'pch',
        'rig', 'dpg', 'premium', 'overtime', 'owed', 'earn',
        'junior assign', 'ja ', 'open time', 'day off',
        'block', 'duty', 'tafd', 'flew', 'flying', 'hours'
    ])

    print(f"[Router] {model_tier.upper()} → {model_name} | Q: {question[:80]}")
    if model_tier != 'simple':
        print(f"[Prompt] Pay sections: {'INJECTED' if is_pay_question else 'SKIPPED'} | max_tokens: {2000 if model_tier == 'complex' else 1500}")

    # --- BUILD SYSTEM PROMPT (tiered by complexity) ---
    
    if model_tier == 'simple':
        # Haiku gets a compact prompt — just the essentials
        system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA).

SCOPE: This tool ONLY searches the {airline_name} JCBA. No FARs, company manuals, or other policies.

RULES:
1. Quote exact contract language with section and page citations
2. Never interpret beyond what the contract explicitly states
3. Use neutral language ("the contract states" not "you get")
4. Acknowledge when the contract is silent

STATUS: 🔵 CLEAR (unambiguous answer), 🔵 AMBIGUOUS (multiple interpretations), 🔵 NOT ADDRESSED (no relevant language)

FORMAT:
📄 CONTRACT LANGUAGE: [Exact quote] 📍 [Section, Page]
📝 EXPLANATION: [Plain English]
🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence]
⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.

Do NOT use dollar signs ($) — write amounts without them (Streamlit renders $ as LaTeX)."""
        max_tokens = 1000
    else:
        # Sonnet and Opus get the full system prompt
        # Pay-specific prompt sections — only injected when relevant
        pay_prompt_sections = ""
        if is_pay_question:
            pay_prompt_sections = """
CURRENT PAY RATES:
DOS = July 24, 2018. Per Section 3.B.3, rates increase 2% annually on DOS anniversary. As of February 2026: 7 increases (July 2019–2025). CURRENT RATE = Appendix A DOS rate × 1.14869. Always use DOS column, multiply by 1.14869, show math. If longevity year is stated, look up that rate in Appendix A and calculate. Do NOT say you cannot find the rate if a year is provided.

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

        system_prompt = f"""You are a neutral contract reference tool for the {airline_name} pilot union contract (JCBA). Provide accurate, unbiased analysis based solely on contract language provided.

SCOPE: This tool ONLY searches the {airline_name} JCBA. It has NO access to FARs, company manuals/SOPs, company policies/memos, other labor agreements, or employment laws. If asked about these, state: "This tool only searches the {airline_name} pilot contract (JCBA) and cannot answer questions about FAA regulations, company manuals, or other policies outside the contract."

CONVERSATION CONTEXT: Use conversation history for follow-ups. Maintain same position, aircraft type, and parameters unless explicitly changed. Always provide complete answers with full citations even for follow-ups.

CORE PRINCIPLES:
1. Quote exact contract language with section and page citations
2. Never interpret beyond what the contract explicitly states
3. Never assume provisions exist that are not in the provided text
4. Use neutral language ("the contract states" not "you get" or "company owes")
5. Acknowledge when the contract is silent; cite all applicable provisions
6. Read ALL provided sections before answering — look across pay, scheduling, reserve, and hours of service

ANALYSIS RULES:
- Check for defined terms — many words have specific contract definitions
- Note qualifiers: "shall" vs "may", "except", "unless", "notwithstanding", "provided"
- Distinguish: "scheduled" vs "actual", "assigned" vs "awarded"
- Distinguish pilot categories: Regular Line, Reserve (R-1/R-2/R-3/R-4), Composite, TDY, Domicile Flex
- Distinguish assignment types: Trip Pairings, Reserve Assignments, Company-Directed, Training, Deadhead

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
{pay_prompt_sections}
SCHEDULING/REST RULES:
- Check across Section 13 (Hours of Service), Section 14 (Scheduling), Section 15 (Reserve)
- Different line types have different rules — cite which line type each provision applies to
- Distinguish "Day Off" (defined term) from "Rest Period" (defined term)

STATUS DETERMINATION:
🔵 CLEAR = Contract explicitly and unambiguously answers; no conflicting provisions
🔵 AMBIGUOUS = Multiple interpretations possible, conflicting provisions, missing scenario details needed to determine which rule applies, or premium trigger conditions not confirmed
🔵 NOT ADDRESSED = Contract contains no relevant language

RESPONSE FORMAT:
📄 CONTRACT LANGUAGE: [Exact quote] 📍 [Section, Page]
(Repeat for each provision)
📝 EXPLANATION: [Plain English analysis]
  Include ⏰ EXTENSION / DAY OFF DUTY ANALYSIS when duty crosses past RAP or into Day Off
  Include ⚠️ OVERTIME SCOPE DISPUTE only when duty starts on a workday and extends into a Day Off (not for pure Day Off duty like JA)
🔵 STATUS: [CLEAR/AMBIGUOUS/NOT ADDRESSED] - [One sentence justification]
⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes.

Every claim must trace to a specific quoted provision. Do not speculate about "common practice" or reference external laws unless the contract itself references them.

Do NOT use dollar signs ($) — write amounts without them (Streamlit renders $ as LaTeX)."""
        # Standard gets 1500, Complex gets 2000
        max_tokens = 2000 if model_tier == 'complex' else 1500

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
"""

    # Inject pre-computed pay reference if applicable (already computed above for routing)
    if pay_ref:
        user_content += f"\n{pay_ref}\n"

    # Inject grievance pattern alerts if applicable (already computed above for routing)
    if grievance_ref:
        user_content += f"\n{grievance_ref}\n"

    user_content += "\nAnswer:"

    messages.append({"role": "user", "content": user_content})

    message = anthropic_client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral", "ttl": "1h"}
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

    return answer, status, response_time, model_tier

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

# Fixed-value contract rules for instant lookup (no API call)
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

# Per diem is computed dynamically based on current date
def _get_per_diem_answer():
    """Build per diem Tier 1 answer with current rates based on anniversary increases."""
    dos_date = datetime(2018, 7, 24)
    now = datetime.now()
    # Count anniversaries: each July 24 after DOS
    anniversaries = now.year - dos_date.year
    if (now.month, now.day) < (dos_date.month, dos_date.day):
        anniversaries -= 1
    anniversaries = max(0, anniversaries)

    base_domestic = 56
    base_international = 72
    current_domestic = base_domestic + anniversaries
    current_international = base_international + anniversaries

    return f"""📄 CONTRACT LANGUAGE: "For Duty or other Company-Directed Assignments that are performed within the Contiguous United States, including all time during a layover in the United States, Fifty-Six Dollars ($56) per Day."
📍 Section 6.C.2.a, Page 99

"For Duty or other Company-directed Assignment that contains a segment that is to or from an airport outside the contiguous United States, including all layover time in a location outside of the contiguous United States: Seventy-Two Dollars ($72) per Day."
📍 Section 6.C.2.b, Page 100

"The Per Diem rates, as provided in subparagraph 6.C., shall be increased by one (1) Dollar ($1.00) per Day on each anniversary date of the Agreement."
📍 Section 6.C.2.c, Page 100

📝 EXPLANATION: Per the contract, pilots receive Per Diem for duty assignments that include rest periods away from their domicile. The base rates (DOS July 24, 2018) were 56/day domestic and 72/day international. Per Section 6.C.2.c, rates increase by 1/day on each contract anniversary.

As of today, there have been {anniversaries} anniversary increases (July 2019 through July {dos_date.year + anniversaries}):
- Domestic (contiguous U.S.): 56 + {anniversaries} = **{current_domestic}/day**
- International: 72 + {anniversaries} = **{current_international}/day**

Per Diem is calculated from the time of scheduled or actual report time at Domicile (whichever is later) until the scheduled or actual conclusion of duty at Domicile (whichever is later). Per Diem is only paid for assignments that include a rest period away from Domicile (Section 6.C.1).

🔵 STATUS: CLEAR - The contract explicitly states per diem rates in Section 6.C.2 and the annual increase formula in Section 6.C.2.c.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

# Per diem keywords checked separately in tier1_instant_answer
_PER_DIEM_KEYWORDS = ['per diem', 'per diem rate', 'what is per diem', 'how much is per diem',
                      'per diem amount', 'meal allowance', 'daily meal', 'per diem pay']

def _match_tier1_rule(question_lower):
    """Check if a question matches a Tier 1 fixed-value rule.
    Returns the rule key or None."""
    for rule_key, rule in TIER1_RULES.items():
        if any(kw in question_lower for kw in rule['keywords']):
            return rule_key
    return None

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


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

    return answer

def _format_definition_answer(term, definition):
    """Build a formatted definition answer matching the app's output style."""
    display_term = term.upper() if len(term) <= 4 else term.title()

    answer = f"""📄 CONTRACT LANGUAGE: "{display_term}: {definition}" 📍 Section 2 (Definitions), Pages 13-45

📝 EXPLANATION: Per Section 2 (Definitions) of the contract, **{display_term}** is defined as: {definition}

🔵 STATUS: CLEAR - The contract explicitly defines this term in Section 2.


⚠️ Disclaimer: This information is for reference only and does not constitute legal advice. Consult your union representative for guidance on contract interpretation and disputes."""

    return answer

def tier1_instant_answer(question_lower):
    """
    Check if a question can be answered instantly without API call.
    Returns (answer, status, response_time) or None if not a Tier 1 question.
    """
    start = time.time()

    # --- TIER 1 RULE LOOKUPS (check BEFORE scenario detection) ---
    # These are "what is the rule?" questions that match keywords also
    # found in scenarios, so they must be checked first.
    # Only triggers on clean rule-lookup phrasing, not scenario context.
    rule_key = _match_tier1_rule(question_lower)
    if rule_key:
        # Extra guard: if the question contains specific numeric scenario details,
        # fall through to the API instead (e.g., "I had 8 hours rest after 16 hour duty")
        has_numeric_scenario = re.search(r'\d+(?:\.\d+)?\s*hours?\s*(?:of\s+)?(?:duty|rest|block|on duty)', question_lower)
        if not has_numeric_scenario:
            answer = TIER1_RULES[rule_key]['answer']
            return answer, 'CLEAR', round(time.time() - start, 1)

    # --- PER DIEM (computed dynamically based on current date) ---
    if any(kw in question_lower for kw in _PER_DIEM_KEYWORDS):
        answer = _get_per_diem_answer()
        return answer, 'CLEAR', round(time.time() - start, 1)

    # --- SCENARIO DETECTION: If question has duty/block/TAFD numbers, skip Tier 1 ---
    # These need the full API with pre-computed pay calculator
    scenario_indicators = ['duty', 'block', 'tafd', 'flew', 'flying', 'flight time',
                           'time away', 'junior assign', 'ja ', 'open time pick',
                           'extension', 'reassign', 'day off', 'overtime',
                           'hour duty', 'hour block', 'hours of duty', 'hours of block',
                           'landed', 'released', 'departed', 'called at', 'got called',
                           'departure', 'what do i get paid', 'what would i get paid',
                           'what should i get paid', 'what am i owed',
                           'rap was', 'rap from', 'my rap', 'on reserve']
    has_scenario = any(s in question_lower for s in scenario_indicators)
    # Also catch time references: "3pm", "noon", "midnight", "0600", etc.
    if not has_scenario:
        has_scenario = bool(re.search(r'\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)|noon|midnight|\d{4}\s*(?:ldt|local|zulu)', question_lower))
    if has_scenario:
        return None

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
# QUESTION PREPROCESSOR
# Normalizes pilot shorthand, abbreviations, and slang before
# the question hits Tier 1, BM25, embeddings, and the API.
# ============================================================

# Order matters: longer patterns first to avoid partial replacements
_SHORTHAND_MAP = [
    # Contractions and informal
    (r"\bwhats\b", "what is"),
    (r"\bwhat's\b", "what is"),
    (r"\bhow's\b", "how is"),
    (r"\bcan't\b", "cannot"),
    (r"\bdon't\b", "do not"),
    (r"\bdoesn't\b", "does not"),
    (r"\bwon't\b", "will not"),
    (r"\bdidn't\b", "did not"),
    (r"\bwasn't\b", "was not"),
    (r"\bi'm\b", "i am"),
    (r"\bi've\b", "i have"),
    (r"\bi'd\b", "i would"),
    # Pilot shorthand — positions
    (r"\bca\b", "captain"),
    (r"\bcapt\b", "captain"),
    (r"\bfo\b", "first officer"),
    (r"\bf/o\b", "first officer"),
    (r"\bpic\b", "pilot in command"),
    (r"\bsic\b", "second in command"),
    # Reserve types
    (r"\br1\b", "r-1"),
    (r"\br2\b", "r-2"),
    (r"\br3\b", "r-3"),
    (r"\br4\b", "r-4"),
    # Pilot shorthand — operations
    (r"\bja'd\b", "junior assigned"),
    (r"\bja'ed\b", "junior assigned"),
    (r"\bjaed\b", "junior assigned"),
    (r"\bja\b", "junior assignment"),
    (r"\bext'd\b", "extended"),
    (r"\bexted\b", "extended"),
    (r"\bdeadhd\b", "deadhead"),
    (r"\bdh\b", "deadhead"),
    (r"\bd/h\b", "deadhead"),
    (r"\bmx\b", "mechanical"),
    (r"\bmech\b", "mechanical"),
    (r"\bpax\b", "passenger"),
    (r"\bsked\b", "schedule"),
    (r"\bskd\b", "schedule"),
    (r"\bdom\b", "domicile"),
    (r"\bvac\b", "vacation"),
    (r"\bprobat\b", "probation"),
    (r"\bgriev\b", "grievance"),
    # Time/pay shorthand
    (r"\byr\b", "year"),
    (r"\byrs\b", "years"),
    (r"\bhr\b", "hour"),
    (r"\bhrs\b", "hours"),
    (r"\bmin\b(?!imum)", "minutes"),
    (r"\bmos?\b", "months"),
    (r"\bOT\b", "overtime"),
    (r"\bot\b", "overtime"),
    # Contract references
    (r"\bsect\b", "section"),
    (r"\bsec\b", "section"),
    (r"\bart\b", "article"),
    (r"\bloa\b", "loa"),
    (r"\bmou\b", "mou"),
    (r"\bjcba\b", "contract"),
    (r"\bcba\b", "contract"),
    # Aircraft
    (r"\b73\b", "b737"),
    (r"\b737\b", "b737"),
    (r"\b76\b", "b767"),
    (r"\b767\b", "b767"),
    # Common misspellings
    (r"\bscheudle\b", "schedule"),
    (r"\bschedual\b", "schedule"),
    (r"\bgrievence\b", "grievance"),
    (r"\bgreivance\b", "grievance"),
    (r"\bassigment\b", "assignment"),
    (r"\breassigment\b", "reassignment"),
    (r"\bpayed\b", "paid"),
    (r"\brecieve\b", "receive"),
    (r"\bcapatin\b", "captain"),
    (r"\bcompensaton\b", "compensation"),
    (r"\bextention\b", "extension"),
    (r"\bdomocile\b", "domicile"),
    (r"\bsenority\b", "seniority"),
    (r"\bseniortiy\b", "seniority"),
    # Additional pilot abbreviations
    (r"\bslb\b", "sick leave bank"),
    (r"\birop\b", "irregular operations"),
    (r"\birops\b", "irregular operations"),
    (r"\bsap\b", "schedule adjustment period"),
    (r"\bmpg\b", "monthly pay guarantee"),
    (r"\bpcd\b", "portable communications device"),
    (r"\bcrew sked\b", "crew scheduling"),
    (r"\bcrewsked\b", "crew scheduling"),
    (r"\bdo\b(?=\s+(?:said|says|told|called|require))", "director of operations"),
    (r"\bexco\b", "executive council"),
    (r"\balpa\b", "union"),
    (r"\bioe\b", "initial operating experience"),
    (r"\bfars\b", "federal aviation regulations"),
    (r"\bldt\b", "local domicile time"),
]

# Pre-compile patterns for performance
_SHORTHAND_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _SHORTHAND_MAP]

def preprocess_question(question_text):
    """Normalize pilot shorthand and abbreviations for better matching."""
    result = question_text
    for pattern, replacement in _SHORTHAND_COMPILED:
        result = pattern.sub(replacement, result)
    # Collapse multiple spaces
    result = re.sub(r'  +', ' ', result).strip()
    return result

# ============================================================
# MAIN ENTRY
# ============================================================
def ask_question(question, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history=None):
    normalized = preprocess_question(question.strip()).lower()

    # Tier 1: Instant answers — no API cost, no embedding cost
    tier1_result = tier1_instant_answer(normalized)
    if tier1_result is not None:
        return tier1_result

    # Always check cache first — regardless of conversation history
    question_embedding = get_embedding_cached(normalized, openai_client)
    semantic_cache = get_semantic_cache()
    cached_result = semantic_cache.lookup(question_embedding, contract_id)
    if cached_result is not None:
        cached_answer, cached_status, cached_time = cached_result
        return cached_answer, cached_status, 0.0

    answer, status, response_time, model_tier = _ask_question_api(
        normalized, chunks, embeddings, openai_client, anthropic_client, contract_id, airline_name, conversation_history
    )

    # Only cache CLEAR and AMBIGUOUS answers — never cache NOT_ADDRESSED
    # A NOT_ADDRESSED might be a retrieval miss; next attempt could succeed
    if status != 'NOT_ADDRESSED':
        semantic_cache.store(question_embedding, normalized, answer, status, response_time, contract_id)

    # "Did you mean?" — append suggestions when NOT_ADDRESSED
    if status == 'NOT_ADDRESSED':
        suggestions = _get_did_you_mean(normalized)
        if suggestions:
            answer += suggestions

    return answer, status, response_time


def _get_did_you_mean(question_lower):
    """Suggest related Quick Reference Cards and Tier 1 topics for NOT_ADDRESSED answers."""
    suggestions = []

    # Map keywords to Quick Reference Card titles
    qrc_matches = {
        'pay': ['Pay Calculation Guide', 'What is a Pay Discrepancy?'],
        'paid': ['Pay Calculation Guide', 'What is a Pay Discrepancy?'],
        'rate': ['Pay Calculation Guide'],
        'rig': ['Pay Calculation Guide'],
        'dpg': ['Pay Calculation Guide'],
        'overtime': ['Pay Calculation Guide', 'Extension Rules'],
        'premium': ['Pay Calculation Guide', 'Junior Assignment Rules'],
        'reserve': ['Reserve Types & Definitions'],
        'r-1': ['Reserve Types & Definitions'],
        'r-2': ['Reserve Types & Definitions'],
        'r-3': ['Reserve Types & Definitions'],
        'r-4': ['Reserve Types & Definitions'],
        'fifo': ['Reserve Types & Definitions'],
        'day off': ['Minimum Days Off / Availability', 'Junior Assignment Rules'],
        'days off': ['Minimum Days Off / Availability'],
        'schedule': ['Minimum Days Off / Availability'],
        'line': ['Minimum Days Off / Availability'],
        'extension': ['Extension Rules'],
        'extended': ['Extension Rules'],
        'junior assign': ['Junior Assignment Rules'],
        'ja ': ['Junior Assignment Rules'],
        'grievance': ['How to File a Grievance', 'What Evidence to Save'],
        'grieve': ['How to File a Grievance', 'What Evidence to Save'],
        'dispute': ['How to File a Grievance', 'What Evidence to Save'],
        'evidence': ['What Evidence to Save'],
        'open time': ['Open Time & Trip Pickup'],
        'trip trade': ['Open Time & Trip Pickup'],
        'pickup': ['Open Time & Trip Pickup'],
    }

    matched_cards = set()
    for keyword, cards in qrc_matches.items():
        if keyword in question_lower:
            matched_cards.update(cards)

    if matched_cards:
        card_list = ', '.join(f'**{c}**' for c in list(matched_cards)[:3])
        suggestions.append(f"\n\n💡 **Related Quick Reference Cards:** {card_list} — available from the Quick Reference menu above.")

    # Suggest trying rephrased question
    suggestions.append("\n\n🔄 **Tip:** Try rephrasing your question with specific contract terms (e.g., \"Section 6\" or \"per diem\" or \"reserve reassignment\"). The search works best with exact contract language.")

    return ''.join(suggestions)

# ============================================================
# ANALYTICS DASHBOARD
# ============================================================
def _load_top_questions():
    """Load top 5 most asked questions via logger (Turso or local fallback)."""
    try:
        logger = init_logger()
        contract_id = st.session_state.get('selected_contract')
        return logger.get_top_questions(5, contract_id=contract_id)
    except:
        return []

def render_analytics_dashboard():
    """Render simple public analytics — just top questions."""
    st.markdown("## 🔥 Most Asked Questions")
    st.caption("See what other pilots are asking about")
    
    top = _load_top_questions()
    
    if top:
        for i, (q_text, count) in enumerate(top, 1):
            label = f"**{i}.** {q_text}"
            if count > 1:
                label += f"  ·  *asked {count} times*"
            st.markdown(label)
    else:
        st.caption("No questions logged yet. Be the first to ask!")

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
if 'show_analytics' not in st.session_state:
    st.session_state.show_analytics = False
if 'ratings' not in st.session_state:
    st.session_state.ratings = {}

# ============================================================
# LOGIN
# ============================================================
if not st.session_state.authenticated:
    st.title("✈️ AskTheContract - Beta Access")
    st.write("**Contract Language Search Engine for Pilots**")

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
    st.markdown("**Search and retrieve exact contract language with page and section references.**")
    st.caption("Provides a plain-language summary of the relevant contract text and highlights whether the language appears clear or ambiguous.")

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

        for card_name, card_data in QUICK_REFERENCE_CARDS.items():
            if st.button(f"{card_data['icon']} {card_name}", key=f"ref_{card_name}", use_container_width=True):
                st.session_state.show_reference = card_name
                st.session_state.show_analytics = False

        st.write("---")
        if st.button("🔥 Most Asked Questions", use_container_width=True):
            st.session_state.show_analytics = not st.session_state.show_analytics
            st.session_state.show_reference = None
            st.rerun()
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.conversation = []
            st.session_state.show_reference = None
            st.rerun()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # ---- MAIN CONTENT ----
    st.info(f"Limited to the {airline_name} Pilot Contract (JCBA). Does not reference FAA regulations, company manuals, or other policies.")

    # Show Quick Reference Card if selected
    if st.session_state.show_reference:
        card = QUICK_REFERENCE_CARDS[st.session_state.show_reference]
        st.markdown(card['content'])
        if st.button("✖ Close Reference Card"):
            st.session_state.show_reference = None
            st.rerun()
        st.write("---")

    # Show Analytics Dashboard if selected
    if st.session_state.show_analytics:
        render_analytics_dashboard()
        if st.button("✖ Close"):
            st.session_state.show_analytics = False
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
                response_time=response_time,
                category=category
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

            # Bottom row
            col1, col2, col3, col4 = st.columns([1, 1, 3, 1])

            # FEATURE 4: Answer Rating
            rating_key = f"rating_{q_num}"
            with col1:
                if st.button("👍", key=f"up_{q_num}"):
                    log_rating(qa['question'], "up", st.session_state.selected_contract)
                    st.session_state.ratings[rating_key] = "up"
            with col2:
                if st.button("👎", key=f"down_{q_num}"):
                    log_rating(qa['question'], "down", st.session_state.selected_contract)
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
