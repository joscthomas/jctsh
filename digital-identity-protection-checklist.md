# Digital Identity Protection Checklist
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step checklist for Joseph and Robin to close the single-point-of-failure risks described in the TIME article "How a Stranger Used One Text Message to Steal My Entire Digital Life" (July 2026).
**Version:** 2.3
**Version description:** Corrected the "ID document photos" plan — RoboForm cannot store document images (text fields only), so the plan now moves Google Photos copies into Locked Folder (not RoboForm) instead of deleting them, with a locator note (not a link) in RoboForm. Updated the matching Phase 5 travel item to reference Locked Folder instead of RoboForm Identity.

---

## Active Cards

CARD-0034 (the original "complete this checklist" card) closed 2026-07-17 as **version 1 done** — the core phone/SIM-swap single-point-of-failure work is solid. Ongoing work is tracked via two follow-on cards (full scope in `kanban-board.md`, not duplicated here):

- **CARD-0071** (Planning) · Emergency Access preparation — RoboForm Emergency Access + Google Inactive Account Manager, testing both, documentation needs, meeting with the designated contact. Covers the checklist's Phase 2 "Password manager" items on this topic.
- **CARD-0072** (Build) · Digital Identity Checklist Version 2 — works through this checklist's remaining open items toward v3.0.

---

## Phase 1 — Lock the Front Door (this week)

### Carrier (do for both lines)
- [X] Call carrier and add a port-out PIN / number lock (T-Mobile: "Account Takeover Protection," Verizon: "Number Lock," AT&T: "Extra Security PIN")
    - Enabled number lock on all lines (2026/07/08)
- [X] Confirm SIM swap requires in-person ID or the PIN, not just knowledge of SSN/DOB
  - Enabled SIM protection on all lines (2026/07/08)
- [X] Robin: same steps on her line/carrier

### Google Account (do for both)
- [X] Change Google Account PIN
- [X] Delete security question
- [X] Delete recovery phone number (Joseph and Robin) — once hardware keys are registered and confirmed working
- [X] Recovery email address confirmed: cross-set to spouse's Gmail (Joseph's account recovery email = Robin's Gmail; Robin's account recovery email = Joseph's Gmail)
- [X] Order 3 Google Titan security keys (1 for Joseph, 1 for Robin, 1 shared backup for the safe)
- [X] Register Joseph's Titan as a passkey on his Google Account
- [X] Register Robin's Titan as a passkey on her Google Account
- [X] Register the shared/backup Titan as a passkey on both accounts
- [X] Store the shared/backup Titan in the safe (see Safe Contents manifest below)
- [X] Set up Windows Hello as a passkey on Joseph's laptop
- [X] Review "recent security activity" / connected devices, remove anything unrecognized or old
- [N] Consider enrolling in Google Advanced Protection Program if either of you handles significant money
- [X] App passwords: Joseph reviewed Security → "App passwords" and revoked any existing ones (these bypass 2-Step Verification/hardware key requirements)
- [ ] App passwords: Robin to review and revoke any existing app passwords
- [ ] Review "Third-party apps & services" with account access (Security settings), revoke unused/old connections — do for both
- [ ] *(Under consideration)* Enable "Skip password when possible" so the passkey/hardware key becomes the default sign-in path instead of falling back to the password — holding off because always having the physical key on hand for everyday sign-in is an unfamiliar habit; want to live with the key day-to-day before locking this in
- [X] Confirm Google Account password itself (distinct from the PIN) is long, unique, generated, and stored in RoboForm
- [ ] Set up Google Inactive Account Manager (Security settings) — define a trusted contact and inactivity timeout for account access/notification
- [X] Confirm 2-Step Verification is enabled account-wide (foundation for everything above) — confirmed on
- [X] Confirm no phone-based method remains under Google 2-Step Verification itself (distinct from the recovery phone already removed) — removed for both accounts
- [X] Set a PIN on all three Titan keys (Joseph, Robin, shared/backup) and test each
- [N] Fire-drill test: sign out and back in with each key from a different device — declined, too involved

### Credit (do for both, now — not after an incident)
- [X] Freeze credit at Equifax
- [X] Freeze credit at Experian
- [X] Freeze credit at TransUnion
- [ ] Freeze at ChexSystems (received error trying to register for an account)
- [ ] Freeze at LexisNexis (why this company? I don't want to create more accounts.)

---

## Phase 2 — Break the Single Point of Failure (this month)

### Dedicated recovery phone number (for non-Google accounts)
- [N] Set up a second, low-profile phone number (Google Voice or second carrier line) — now scoped specifically to institutions that still require phone-based 2FA and don't support passkeys/hardware keys (e.g., banks, brokerages, the credit union), since Google's own recovery phone is being removed in favor of hardware keys
- [N] If using Google Voice, set a recurring reminder to keep it active (3-month inactivity reclaim policy), or use a small autopay carrier line instead to avoid the upkeep

### Password manager (RoboForm)
- [X] RoboForm in use for password management (long-standing)
- [X] RoboForm 2FA enabled via Google Authenticator
- [X] Add hardware-key 2FA to RoboForm once Titans arrive (confirmed supported: YubiKey Security Key C NFC / Google Titan)
- [N] Confirm Robin has her own independent RoboForm login/vault access, not dependent on a shared password (Robin uses my account)
- [ ] Evaluate RoboForm Emergency Access (grants a designated person access to credentials upon death or incapacitation) — decide who the designated contact should be. **Reasoning:** both Joseph and Robin have the master password memorized, so each already has full, immediate access if something happens to the other — no designee or waiting period needed for that case. Emergency Access therefore only matters for the scenario where *both* are unavailable at once, which means the designated contact should be a third party (most likely one of the adult children, consistent with their existing role as Google Recovery Contacts), not each other. Still need to pick which child.
- [ ] Test the Emergency Access flow end-to-end once configured (trigger a request, confirm the deny/delay notification works, confirm the waiting period is tuned right) — don't just configure it and assume it works
- [ ] Store the shared household PIN's resulting value (not the source word, not the derivation method) as a RoboForm secure note, labeled plainly with what it unlocks — Emergency Access then hands it to the designated contact automatically along with everything else, with no separate handoff needed
- [X] Move to unique, generated passwords for bank, brokerage, crypto, and email accounts first if not already done

### ID document photos — consolidate and clean up
- [ ] Add passport/DL numbers and expiration dates (Joseph and Robin) to RoboForm Identity entries — **correction:** RoboForm's Identity feature only stores structured text fields (number, dates), not document images/attachments; earlier guidance claiming image support was wrong
- [ ] Move digital photos of IDs (DL, passport, credit/debit cards, etc.) that currently sit in Google Photos' general library into a **Locked Folder** (Security → Locked Folder) — excluded from search/Memories/family sharing, gated by device passcode/biometric on top of the account login, cross-device backed up, and content inside can't be link-shared without first being moved out
- [ ] Add a locator note in RoboForm (not a link — Locked Folder content can't be link-shared anyway) pointing to where the photos live, e.g. "ID photos: Google Photos → Locked Folder"
- [ ] Search Immich (self-hosted photo library, `photo-server`) for the same — delete; Immich has no equivalent protected-folder feature, so it doesn't get a "move to" option here
- [ ] Check other likely locations: phone camera roll (pre-cloud-sync), email attachments/sent items, text/messaging apps — delete, or move into Locked Folder if worth keeping
- [ ] Confirm no lingering copies remain in cloud photo trash/recently-deleted folders — Google Photos and Immich both hold deleted items for a retention window before permanent removal, so deleting isn't done until that window passes too

> **Why this matters:** ID photos sitting in a general-purpose photo library (searchable, auto-organized/face-indexed, exposed to Memories resurfacing and family sharing) are easy to expose accidentally, even without a targeted attack. Locked Folder is Google's purpose-built answer — it inherits this account's existing hardening (hardware-key-only 2FA, no phone-based fallback) and adds a second, local gate on top. RoboForm can't hold the images at all, so it isn't part of the storage plan for the photos themselves — only for the passport/DL numbers, which are genuine text data it does support.

### Recovery contacts
- [ ] Set Google Account Recovery Contacts: Robin ↔ Joseph (each other)
- [ ] Add both children as recovery contacts (confirmed: both are adults, each with their own independent Google account)
- [ ] *(Under consideration, not yet implemented)* Shared codeword system with children for identity verification

### Offline hardcopy vault
- [X] Generate Google 2-Step Verification backup codes for Joseph and Robin
- [X] Physically label all three Titan keys (sticker/tape/paint dot marking "J" / "R" / "Backup") — Titan keys have no printed serial number, so a label is the only way to tell the identical units apart; record the labeling scheme in the offline vault
- [ ] Store offline hardcopy in the safe (see Safe Contents manifest below) — decided, current plan
- [ ] *(Under consideration)* Travel copy: a small, unlabeled duplicate carried separately from phone/hardware key while traveling (see Phase 5)
- [ ] *(Under consideration)* Outside-contact copy: a third duplicate held by someone outside the household — see "Outside-Contact Copy Pattern" note below

> **Outside-Contact Copy Pattern:** the safe protects against a lost phone or device; it does not protect against a household-level event — a house fire, a burglary, or both of you traveling together and losing the same bag. A third duplicate of the backup codes/serials, held by someone who lives elsewhere (e.g., one of the children, since both are independent adults), survives exactly that scenario. It doesn't need to be requested often — it just needs to exist for the rare case where both the safe copy and any travel copy are unreachable at once. Same logic as having Recovery Contacts in a different location from your own household.

### General
- [ ] Confirm neither of you can be fully locked out of money and communication by the loss of one single device or account (test/fire-drill)

---

## Safe Contents

Consolidated manifest of everything intended to physically live in the safe. Setup/decision steps for each item live in Phase 1 (Google Account) and Phase 2 (Offline hardcopy vault) above — this section is the single canonical list of what should actually be placed inside, and tracks whether each has been placed yet.

- [X] Shared/backup Titan security key
- [X] Google 2-Step Verification backup codes (Joseph and Robin)
- [X] Note of the key labeling scheme (which physical marking = Joseph's / Robin's / shared-backup)
- [ ] IDs (copies of driver's license/passport, etc.)

**Deliberately excluded:** account numbers and insurance policy numbers. Both already live in RoboForm, which stays current as accounts/policies change; a paper copy would only go stale. The safe's backup Titan key already restores RoboForm access (hardware-key 2FA is enabled there) if you're locked out — so the recovery path is safe → key → RoboForm → current numbers, not a second manually-maintained copy. The one gap this doesn't cover — someone else (executor, recovery contact) needing account numbers without knowing the RoboForm master password — is what RoboForm Emergency Access is for (see Phase 2, Password manager section), not a paper backup.

**Also deliberately excluded: the RoboForm master password itself.** It's the single key to everything else in RoboForm — writing it down anywhere, even in the safe, reintroduces exactly the single-point-of-failure risk this whole checklist exists to close (same bearer-secret logic as crypto seed phrases — see `digital-identity.md`'s "What NOT to Store in RoboForm" section). Emergency Access is the purpose-built answer to "someone else eventually needs in" — it grants access through RoboForm's own mechanism without ever exposing the actual password. If Emergency Access feels too slow for a true emergency, the fix is tuning/testing its waiting period, not writing the password on paper.

---

## Phase 3 — Household Protocol

- [X] Agree: never read a verification code to anyone who calls — hang up, call the number on the back of the card instead
- [X] Agree: any request to move money gets a voice call to confirm, even if the text/app notification appears to come from each other
- [X] Decide whether a shared verbal codeword is worth adding for ambiguous/urgent requests (Joseph ↔ Robin)
- [ ] *(Under consideration, not yet implemented)* Extend codeword system to children
- [ ] Walk through this checklist together so both of you know it exists and where it lives

---

## Phase 4 — Incident Response Plan (keep a copy of this accessible offline)

1. [ ] From another device, use a hardware security key to sign into Google, change the password, and revoke all active sessions immediately
2. [ ] Call carrier to lock/freeze the SIM before anything else
3. [ ] Call banks/brokerages/credit union using the number on the card/statement — never a number that contacted you
4. [ ] File a report at identitytheft.gov (FTC)
5. [ ] File a police report and get the report number
6. [ ] Document everything as you go: timestamps, amounts, reference numbers, names of who you spoke to

---

## Phase 5 — Travel Considerations

- [ ] Carry hardware keys separately (not both/all in the same bag) — Joseph's key on Joseph, Robin's key on Robin
- [ ] Leave the shared/backup Titan key at home; don't travel with all three keys at once
- [ ] Confirm at least one 2FA method traveling with you is independent of your phone (hardware key or laptop passkey)
- [ ] Check dual-SIM/eSIM setup keeps your home number active alongside any local SIM used abroad
- [ ] Call carrier before international travel to confirm the port-out lock isn't relaxed for roaming support scenarios
- [ ] Carry a travel copy of backup codes — small, unlabeled, kept separate from phone and hardware key
- [ ] Brief recovery contacts (Robin, children, any outside contact) on travel dates before departure
- [ ] Carry a non-digital payment fallback: physical card plus some cash
- [ ] Notify banks/credit union of travel dates
- [ ] Confirm digital copies of DL/passport (Google Photos Locked Folder) are accessible while traveling — backup if the physical document is lost or stolen abroad; also carry a physical photocopy separate from the passport itself, standard travel-safety practice

---

## Appendix A — Scenario Walkthroughs

**Scenario A — One phone stolen while traveling, other person unaffected.** Hardware key (carried separately from the phone) signs into Google directly on a borrowed device or the other person's phone; carrier port-out lock already blocks SIM swap; Find My Device locks the phone; physical cash/card cover immediate needs. Resolves in minutes without needing a recovery contact.

**Scenario B — Both phones lost/stolen together (bag theft, hotel burglary).** If hardware keys were carried on-person rather than in the stolen bag, each person signs back in independently with their own key. If a key is lost too, fall back to a Recovery Contact: reach them by any available channel, confirm identity with the household codeword, have them relay the Google-generated verification code. Pull account details from the offline vault copy that stayed home or with a trusted contact — not the one that traveled.

**Scenario C — Spoofed "fraud alert" call while traveling.** Hang up on any inbound call asking to read back a code or confirm SSN/DOB, regardless of how convincing it looks. Call the number on the back of the card independently. With no recovery phone left on the Google account and hardware keys required for recovery, the "read me the code" trick has nothing to exploit. If the scammer pivots to the other spouse with a fake payment request, the household protocol (voice confirmation, codeword if needed) blocks it.

---

## Accounts Without 2FA — Compensating Controls (e.g., Credit Union)

- [ ] Ask directly whether 2FA/MFA exists but isn't obvious (may live in the mobile app rather than the website)
- [ ] Ask about setting a verbal password/passphrase required for any phone-based account changes or discussions
- [ ] Turn on every available alert: new-device login, transaction/withdrawal alerts, failed-login alerts
- [ ] Ask if they offer a callback/manual hold requirement for transfers above a set amount
- [ ] Ensure the account password is long, unique, and generated — stored in RoboForm, never reused
- [ ] Limit balance held there long-term; sweep excess to an account with real 2FA
- [ ] Reassess whether this should remain a primary account long-term if 2FA is never added

---

## Open Items to Fill In

- [ ] List specific banks/brokerages/payment apps in use, so carrier- and institution-specific steps can be added
- [X] Confirm current password manager / 2FA setup — RoboForm confirmed in use, hardware-key upgrade pending key delivery
- [X] Confirm children's ages and Google account independence — both are adults with their own independent Google accounts
- [ ] Decide on travel-copy and outside-contact-copy adoption for backup codes/serials (safe copy already decided)
- [ ] Decide who holds RoboForm Emergency Access designee status, if enabled
- [ ] Target: complete hardware key setup (order → registration on both accounts + RoboForm) within ~1 month (by 2026-08-08), since Titans are already on order
- [ ] Set a review date to revisit this checklist (recommend: 6 months, or at hardware key setup completion, whichever comes first)
